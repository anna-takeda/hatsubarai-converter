import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def process_with_input(input_df, error_items, submitted_names):
    """入力された商品名でデータを処理する関数"""
    result_rows = []
    order_id_col = input_df.columns[32]
    grouped = input_df.groupby(input_df[order_id_col])
    
    for order_id, group in grouped:
        row = [""] * len(input_df.columns)
        first_row = group.iloc[0]
        
        # 基本情報を転記
        for i in range(len(input_df.columns)):
            if pd.notna(first_row[i]):
                row[i] = str(first_row[i]).strip()
        
        # エラーアイテムに含まれているかチェック
        error_item = next((item for item in error_items if item['order_id'] == order_id), None)
        
        if error_item:
            # 入力された商品名を使用
            key = f"product_name_{error_item['order_id']}_{error_item['product_code']}"
            if key in submitted_names:
                if error_item['index'] == 0:
                    row[26] = error_item['product_code']
                    row[27] = submitted_names[key]
                elif error_item['index'] == 1:
                    row[28] = error_item['product_code']
                    row[29] = submitted_names[key]
        else:
            # 通常の商品情報処理
            for i, (_, item) in enumerate(group.iterrows()):
                product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                
                if i == 0:
                    row[26] = product_code
                    row[27] = product_name
                elif i == 1:
                    row[28] = product_code
                    row[29] = product_name
        
        result_rows.append(row)
    
    return result_rows

def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    try:
        # 初期化
        if 'error_items' not in st.session_state:
            st.session_state.error_items = []
            st.session_state.input_df = input_df
            
            # エラーアイテムの収集
            order_id_col = input_df.columns[32]
            grouped = input_df.groupby(input_df[order_id_col])
            
            for order_id, group in grouped:
                for i, (_, item) in enumerate(group.iterrows()):
                    product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                    product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                    
                    if not product_name or product_name == 'nan':
                        st.session_state.error_items.append({
                            'order_id': order_id,
                            'product_code': product_code,
                            'index': i
                        })
        
        # エラーアイテムの処理
        if st.session_state.error_items:
            st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
            
            submitted_names = {}
            with st.form("product_names_form"):
                for item in st.session_state.error_items:
                    st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                    key = f"product_name_{item['order_id']}_{item['product_code']}"
                    product_name = st.text_input(f"商品名を入力", key=key)
                    if product_name.strip():
                        submitted_names[key] = product_name
                
                submit_button = st.form_submit_button("入力した商品名で続行")
                
                if submit_button:
                    if len(submitted_names) == len(st.session_state.error_items):
                        # 入力された商品名でデータを処理
                        result_rows = process_with_input(
                            st.session_state.input_df,
                            st.session_state.error_items,
                            submitted_names
                        )
                        
                        # 結果のDataFrame作成
                        result_df = pd.DataFrame(result_rows)
                        
                        # 1行目に空行を追加
                        empty_row = [""] * len(input_df.columns)
                        result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
                        
                        # セッションステートをクリア
                        del st.session_state.error_items
                        del st.session_state.input_df
                        
                        return result_df
                    else:
                        st.error("すべての商品名を入力してください。")
                        return None
            
            return None
        
        # エラーがない場合は通常の処理
        result_rows = process_with_input(input_df, [], {})
        
        if not result_rows:
            raise ValueError("変換結果が空です。入力データを確認してください。")
        
        # 結果のDataFrame作成
        result_df = pd.DataFrame(result_rows)
        
        # 1行目に空行を追加
        empty_row = [""] * len(input_df.columns)
        result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
        
        return result_df
        
    except Exception as e:
        st.error(f"データ処理中にエラーが発生しました: {str(e)}")
        if 'error_items' in st.session_state:
            del st.session_state.error_items
        if 'input_df' in st.session_state:
            del st.session_state.input_df
        return None

def main():
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')
    
    uploaded_file = st.file_uploader(
        'CSVファイルをアップロードしてください',
        type=['csv'],
        help='Shift-JISエンコーディングのCSVファイルを選択してください。'
    )
    
    if uploaded_file:
        try:
            # ヘッダーなしで読み込み、すべての列を文字列として扱う
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            st.success('ファイルの読み込みに成功しました。')
            
            # データプレビュー表示
            st.write('データプレビュー（最初の3行）:')
            st.dataframe(input_df.head(3))
            
            if st.button('変換開始', type='primary'):
                with st.spinner('変換処理中...'):
                    result_df = convert_to_hatabarai(input_df)
                
                if result_df is not None:
                    # 変換結果をCSVとして出力
                    output = io.BytesIO()
                    result_df.to_csv(output, encoding='cp932', index=False, header=False)
                    output.seek(0)
                    
                    st.download_button(
                        label='変換済みCSVをダウンロード',
                        data=output,
                        file_name='hatabarai_output.csv',
                        mime='text/csv'
                    )
                    
                    st.success('✨ 変換が完了しました！')
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')

if __name__ == '__main__':
    main()
