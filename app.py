import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def check_product_count(input_df):
    warnings = []
    order_groups = input_df.groupby(input_df[32])
    
    for order_id, group in order_groups:
        unique_products = set()
        for _, row in group.iterrows():
            if pd.notna(row[26]) and str(row[26]).strip() and str(row[26]) != 'nan':
                unique_products.add(str(row[26]).strip())
        
        if len(unique_products) >= 3:
            warnings.append({
                'order_id': order_id,
                'product_count': len(unique_products),
                'products': list(unique_products)
            })
    
    return warnings

def check_empty_product_names(input_df):
    error_items = []
    order_groups = input_df.groupby(input_df[32])
    
    for order_id, group in order_groups:
        for _, row in group.iterrows():
            product_code = str(row[26]).strip() if pd.notna(row[26]) else ""
            product_name = str(row[27]).strip() if pd.notna(row[27]) else ""
            
            if product_code and (not product_name or product_name == 'nan'):
                error_items.append({
                    'order_id': order_id,
                    'product_code': product_code,
                    'row': row.tolist()
                })
    
    return error_items

def process_data(input_df, error_items):
    updated_df = input_df.copy()
    
    for item in st.session_state.error_items:
        order_mask = updated_df[32] == item['order_id']
        product_mask = updated_df[26] == item['product_code']
        mask = order_mask & product_mask
        
        if any(mask):
            key = f"product_name_{item['order_id']}_{item['product_code']}"
            product_name = st.session_state[key]
            row_idx = mask.idxmax()
            updated_df.at[row_idx, 27] = product_name
    
    empty_row = pd.DataFrame([[""] * len(updated_df.columns)], columns=updated_df.columns)
    result_df = pd.concat([empty_row, updated_df], ignore_index=True)
    return result_df

def main():
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')
    
    if 'error_items' not in st.session_state:
        st.session_state.error_items = []
        st.session_state.submitted = False
        st.session_state.converted_df = None
    
    uploaded_file = st.file_uploader(
        'CSVファイルをアップロードしてください',
        type=['csv'],
        help='Shift-JIS(cp932)エンコーディングのCSVファイルを選択してください。'
    )
    
    if uploaded_file:
        try:
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            st.success('ファイルの読み込みに成功しました。')
            
            product_warnings = check_product_count(input_df)
            if product_warnings:
                st.warning("⚠️ 以下の注文には3つ以上の商品が含まれています：")
                for warn in product_warnings:
                    st.write(f"注文ID: {warn['order_id']}")
                    st.write(f"商品数: {warn['product_count']}")
                    st.write(f"商品コード: {', '.join(map(str, warn['products']))}")
                st.write("---")
            
            # 初期化
            if 'converted_df' not in st.session_state:
                st.session_state.converted_df = None
            
            if not st.session_state.error_items:
                error_items = check_empty_product_names(input_df)
                if error_items:
                    st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
                    st.session_state.error_items = error_items
                    st.session_state.input_df = input_df
            
            st.write('データプレビュー（最初の3行）:')
            st.dataframe(input_df.head(3))
            
            # ========= ここからフォーム内 =========
            if st.session_state.error_items:
                with st.form("product_names_form"):
                    all_filled = True
                    for item in st.session_state.error_items:
                        st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                        key = f"product_name_{item['order_id']}_{item['product_code']}"
                        product_name = st.text_input(
                            "商品名を入力", 
                            key=key
                        )
                        if not product_name.strip():
                            all_filled = False
                    
                    submitted = st.form_submit_button("入力した商品名で続行")
                
                # フォームの外で処理するために、フォームの外でフラグを持たせる
                if submitted:
                    if not all_filled:
                        st.error("すべての商品名を入力してください。")
                    else:
                        try:
                            result_df = process_data(input_df, st.session_state.error_items)
                            # セッションに結果を保存しておく
                            st.session_state.converted_df = result_df
                            st.success("商品名入力が完了しました！ 下のダウンロードボタンからCSVをダウンロードできます。")
                            
                        except Exception as e:
                            st.error(f"データ処理中にエラーが発生しました: {str(e)}")
            
            else:
                # 商品名に空欄がない場合、すぐに変換処理を行う
                try:
                    empty_row = pd.DataFrame([[""] * len(input_df.columns)], columns=input_df.columns)
                    result_df = pd.concat([empty_row, input_df], ignore_index=True)
                    st.session_state.converted_df = result_df
                    st.success('変換が完了しました！ 下のダウンロードボタンからCSVをダウンロードできます。')
                except Exception as e:
                    st.error(f"ファイルの出力中にエラーが発生しました: {str(e)}")
            
            # ========= ここからフォーム外 =========
            if st.session_state.converted_df is not None:
                st.write("変換後のデータプレビュー（最初の3行）:")
                st.dataframe(st.session_state.converted_df.head(3))
                
                # ダウンロードボタンはフォーム外
                output = io.BytesIO()
                st.session_state.converted_df.to_csv(output, encoding='cp932', index=False, header=False, errors='ignore')
                output.seek(0)
                
                st.download_button(
                    label='変換済みCSVをダウンロード',
                    data=output.getvalue(),
                    file_name='hatabarai_output.csv',
                    mime='text/csv'
                )
                
                if st.button('新しい変換を開始'):
                    for key in ['error_items', 'input_df', 'submitted', 'converted_df']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.experimental_rerun()
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')

if __name__ == '__main__':
    main()
