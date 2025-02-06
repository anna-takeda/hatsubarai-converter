import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def check_product_count(input_df):
    """注文ごとの商品数をチェックし、3つ以上ある場合は警告を表示する"""
    warnings = []
    
    # 注文番号でグループ化
    order_groups = input_df.groupby(input_df[input_df.columns[35]])
    
    for order_id, group in order_groups:
        unique_products = set()
        
        # 各商品コード列をチェック
        for code_col in [26, 28, 30]:
            for _, row in group.iterrows():
                if pd.notna(row[code_col]) and str(row[code_col]).strip() and str(row[code_col]) != 'nan':
                    unique_products.add(str(row[code_col]).strip())
        
        if len(unique_products) >= 3:
            warnings.append({
                'order_id': order_id,
                'product_count': len(unique_products),
                'products': list(unique_products)
            })
    
    return warnings

def check_empty_product_names(input_df):
    """商品名が空欄の商品をチェックする"""
    error_items = []
    
    # 注文番号でグループ化
    order_groups = input_df.groupby(input_df[input_df.columns[35]])
    
    for order_id, group in order_groups:
        # 商品コードと商品名の列のペアをチェック
        product_pairs = [(26, 27), (28, 29), (30, 31)]  # (商品コード列, 商品名列)
        
        for code_col, name_col in product_pairs:
            for _, row in group.iterrows():
                product_code = str(row[code_col]).strip() if pd.notna(row[code_col]) else ""
                product_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                
                if product_code and (not product_name or product_name == 'nan'):
                    error_items.append({
                        'order_id': order_id,
                        'product_code': product_code,
                        'row': row.tolist()
                    })
    
    return error_items

def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    try:
        # エラーアイテム処理
        if st.session_state.error_items:
            with st.form("product_names_form"):
                all_filled = True
                for item in st.session_state.error_items:
                    st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                    key = f"product_name_{item['order_id']}_{item['product_code']}"
                    product_name = st.text_input(
                        f"商品名を入力",
                        key=key
                    )
                    if not product_name.strip():
                        all_filled = False
                
                submitted = st.form_submit_button("入力した商品名で続行")
                if submitted:
                    if not all_filled:
                        st.error("すべての商品名を入力してください。")
                    else:
                        st.session_state.submitted = True
                        updated_df = input_df.copy()
                        
                        # 入力された商品名を反映
                        for item in st.session_state.error_items:
                            order_mask = updated_df[updated_df.columns[35]] == item['order_id']
                            for code_col, name_col in [(26, 27), (28, 29), (30, 31)]:
                                code_mask = updated_df[updated_df.columns[code_col]].astype(str).str.strip() == item['product_code']
                                if any(order_mask & code_mask):
                                    key = f"product_name_{item['order_id']}_{item['product_code']}"
                                    name_value = st.session_state[key]
                                    updated_df.loc[order_mask & code_mask, updated_df.columns[name_col]] = name_value
                        
                        # 1行目に空行を追加
                        empty_row = pd.DataFrame([[""] * len(updated_df.columns)], columns=updated_df.columns)
                        result_df = pd.concat([empty_row, updated_df], ignore_index=True)
                        st.session_state.converted_df = result_df
                        
                        # 結果のプレビュー表示
                        st.write("変換後のデータプレビュー（最初の3行）:")
                        st.dataframe(st.session_state.converted_df.head(3))
                        
                        # CSVダウンロードボタン
                        output = io.BytesIO()
                        st.session_state.converted_df.to_csv(output, encoding='cp932', index=False, header=False)
                        output.seek(0)
                        
                        st.download_button(
                            label='変換済みCSVをダウンロード',
                            data=output,
                            file_name='hatabarai_output.csv',
                            mime='text/csv'
                        )
                        
                        st.success('✨ 変換が完了しました！')
                        
                        if st.button('新しい変換を開始'):
                            for key in ['error_items', 'input_df', 'submitted', 'converted_df']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.experimental_rerun()
            
            return None
        
        return input_df
        
    except Exception as e:
        st.error(f"データ処理中にエラーが発生しました: {str(e)}")
        return None

def main():
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')
    
    # セッション状態の初期化
    if 'error_items' not in st.session_state:
        st.session_state.error_items = []
        st.session_state.submitted = False
        st.session_state.converted_df = None
    
    uploaded_file = st.file_uploader(
        'CSVファイルをアップロードしてください',
        type=['csv'],
        help='Shift-JISエンコーディングのCSVファイルを選択してください。'
    )
    
    if uploaded_file:
        try:
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            st.success('ファイルの読み込みに成功しました。')
            
            # 商品数チェック
            product_warnings = check_product_count(input_df)
            if product_warnings:
                st.warning("⚠️ 以下の注文には3つ以上の商品が含まれています：")
                for warn in product_warnings:
                    st.write(f"注文ID: {warn['order_id']}")
                    st.write(f"商品数: {warn['product_count']}")
                    st.write(f"商品コード: {', '.join(map(str, warn['products']))}")
                st.write("---")
            
            # 空の商品名チェック
            if not st.session_state.error_items:
                error_items = check_empty_product_names(input_df)
                if error_items:
                    st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
                    st.session_state.error_items = error_items
                    st.session_state.input_df = input_df
            
            # データプレビュー表示
            st.write('データプレビュー（最初の3行）:')
            st.dataframe(input_df.head(3))
            
            if not st.session_state.error_items:
                # 変換済みCSVダウンロードボタン
                output = io.BytesIO()
                # 1行目に空行を追加
                empty_row = pd.DataFrame([[""] * len(input_df.columns)], columns=input_df.columns)
                result_df = pd.concat([empty_row, input_df], ignore_index=True)
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
                convert_to_hatabarai(input_df)
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')

if __name__ == '__main__':
    main()
