import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def initialize_session_state():
    if 'step' not in st.session_state:
        st.session_state.step = 'upload'
    if 'input_df' not in st.session_state:
        st.session_state.input_df = None
    if 'error_items' not in st.session_state:
        st.session_state.error_items = []
    if 'product_names' not in st.session_state:
        st.session_state.product_names = {}

def reset_session_state():
    st.session_state.step = 'upload'
    st.session_state.input_df = None
    st.session_state.error_items = []
    st.session_state.product_names = {}

def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    try:
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
            
            # 商品情報の処理
            has_error = False
            for i, (_, item) in enumerate(group.iterrows()):
                product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                
                if not product_name or product_name == 'nan':
                    st.session_state.error_items.append({
                        'order_id': order_id,
                        'product_code': product_code,
                        'index': i,
                        'row': row.copy()
                    })
                    has_error = True
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
        
        if st.session_state.error_items:
            st.session_state.step = 'input_names'
            return None
        
        return create_result_df(result_rows, input_df)
        
    except Exception as e:
        st.error(f"データ処理中にエラーが発生しました: {str(e)}")
        return None

def create_result_df(result_rows, input_df):
    """結果のDataFrameを作成する関数"""
    if not result_rows:
        raise ValueError("変換結果が空です。入力データを確認してください。")
    
    # 結果のDataFrame作成
    result_df = pd.DataFrame(result_rows)
    
    # 1行目に空行を追加
    empty_row = [""] * len(input_df.columns)
    result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
    
    return result_df

def handle_product_names_input():
    """商品名入力フォームの処理"""
    st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
    
    with st.form("product_names_form"):
        all_filled = True
        for item in st.session_state.error_items:
            st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
            key = f"product_name_{item['order_id']}_{item['product_code']}"
            product_name = st.text_input(
                f"商品名を入力",
                key=key,
                value=st.session_state.product_names.get(key, "")
            )
            if not product_name.strip():
                all_filled = False
            st.session_state.product_names[key] = product_name
        
        submitted = st.form_submit_button("入力した商品名で続行")
        
        if submitted:
            if all_filled:
                # 入力された商品名でデータを更新
                result_rows = []
                for item in st.session_state.error_items:
                    row = item['row']
                    key = f"product_name_{item['order_id']}_{item['product_code']}"
                    if item['index'] == 0:
                        row[27] = st.session_state.product_names[key]
                    elif item['index'] == 1:
                        row[29] = st.session_state.product_names[key]
                    result_rows.append(row)
                
                result_df = create_result_df(result_rows, st.session_state.input_df)
                
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
                st.session_state.step = 'complete'
            else:
                st.error("すべての商品名を入力してください。")

def main():
    initialize_session_state()
    
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')
    
    if st.session_state.step == 'upload':
        uploaded_file = st.file_uploader(
            'CSVファイルをアップロードしてください',
            type=['csv'],
            help='Shift-JISエンコーディングのCSVファイルを選択してください。'
        )
        
        if uploaded_file:
            try:
                # ヘッダーなしで読み込み、すべての列を文字列として扱う
                input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
                st.session_state.input_df = input_df
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
                        st.session_state.step = 'complete'
                        
            except Exception as e:
                st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')
    
    elif st.session_state.step == 'input_names':
        handle_product_names_input()
        if st.button('最初からやり直す'):
            reset_session_state()
            st.experimental_rerun()
    
    elif st.session_state.step == 'complete':
        if st.button('新しいファイルを変換する'):
            reset_session_state()
            st.experimental_rerun()

if __name__ == '__main__':
    main()
