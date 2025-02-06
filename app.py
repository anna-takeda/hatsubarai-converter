import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def find_empty_product_names(input_df):
    """空の商品名を持つ商品を見つける"""
    error_items = []
    order_id_col = input_df.columns[32]
    grouped = input_df.groupby(input_df[order_id_col])
    
    for order_id, group in grouped:
        for i, (_, item) in enumerate(group.iterrows()):
            product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
            product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
            
            if not product_name or product_name == 'nan':
                error_items.append({
                    'order_id': order_id,
                    'product_code': product_code,
                    'index': i
                })
    
    return error_items

def convert_with_product_names(input_df, product_names):
    """商品名を指定してCSVを変換"""
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
        for i, (_, item) in enumerate(group.iterrows()):
            product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
            product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
            
            key = f"{order_id}_{product_code}"
            if key in product_names:
                product_name = product_names[key]
            
            if i == 0:
                row[26] = product_code
                row[27] = product_name
            elif i == 1:
                row[28] = product_code
                row[29] = product_name
        
        result_rows.append(row)
    
    # 1行目に空行を追加
    empty_row = [""] * len(input_df.columns)
    result_df = pd.DataFrame(result_rows)
    result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
    
    return result_df

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
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            st.success('ファイルの読み込みに成功しました。')
            
            st.write('データプレビュー（最初の3行）:')
            st.dataframe(input_df.head(3))
            
            empty_items = find_empty_product_names(input_df)
            
            if empty_items:
                st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
                
                product_names = {}
                # フォームの外で入力フィールドを作成
                for item in empty_items:
                    st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                    key = f"{item['order_id']}_{item['product_code']}"
                    product_name = st.text_input(f"商品名を入力", key=key)
                    if product_name.strip():
                        product_names[key] = product_name
                
                # 変換ボタン
                if st.button('変換実行', type='primary'):
                    if len(product_names) == len(empty_items):
                        with st.spinner('変換処理中...'):
                            result_df = convert_with_product_names(input_df, product_names)
                            
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
                    else:
                        st.error("すべての商品名を入力してください。")
            
            else:
                if st.button('変換実行', type='primary'):
                    with st.spinner('変換処理中...'):
                        result_df = convert_with_product_names(input_df, {})
                        
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
            st.error(f'⚠️ エラーが発生しました: {str(e)}')

if __name__ == '__main__':
    main()
