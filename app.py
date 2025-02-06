import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    try:
        # 注文IDで行をグループ化（CSVの見た目の33列目の注文番号）
        order_id_col = input_df.columns[32]
        grouped = input_df.groupby(input_df[order_id_col])
        
        result_rows = []
        error_items = []
        
        for order_id, group in grouped:
            # 42列分の空の配列を作成
            row = [""] * len(input_df.columns)
            
            # 基本情報を転記
            first_row = group.iloc[0]
            for i in range(len(input_df.columns)):
                if pd.notna(first_row[i]):
                    row[i] = str(first_row[i]).strip()
            
            # 商品情報の処理
            has_error = False
            for i, (_, item) in enumerate(group.iterrows()):
                product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                
                if not product_name or product_name == 'nan':
                    has_error = True
                    error_items.append({
                        'order_id': order_id,
                        'product_code': product_code,
                        'index': i,
                        'row': row.copy()
                    })
                    break
                
                if i == 0:
                    row[26] = product_code
                    row[27] = product_name
                elif i == 1:
                    row[28] = product_code
                    row[29] = product_name
                elif i > 1:
                    raise ValueError(f"受注ID {order_id} に3つ以上の商品が含まれています。")
            
            if not has_error:
                result_rows.append(row)
        
        # エラーアイテムの処理
        if error_items:
            st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
            
            with st.form("product_names_form"):
                for item in error_items:
                    st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                    new_product_name = st.text_input(
                        f"商品名を入力",
                        key=f"product_name_{item['order_id']}_{item['product_code']}"
                    )
                    
                    if new_product_name:
                        row = item['row']
                        if item['index'] == 0:
                            row[27] = new_product_name
                        elif item['index'] == 1:
                            row[29] = new_product_name
                        result_rows.append(row)
                
                if st.form_submit_button("入力した商品名で続行"):
                    if len(result_rows) < len(grouped):
                        st.error("すべての商品名を入力してください。")
                        return None
                else:
                    return None
        
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
