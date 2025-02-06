import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="発払いCSV変換ツール",
    page_icon="📝",
    layout="centered"
)

# --- 商品数警告チェック（3つ以上ある注文に対して警告） ---
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

# --- 受注IDごとに行をまとめる処理 ---
def combine_rows_by_order_id_new(df):
    """
    同じ受注ID（列32）ごとに行をまとめる。
      - 1つ目の行をベース行とする。
      - もし2行目があれば、2行目の「商品ID」（列26）をベース行の AC 列（0-based で28列目）に、
        また2行目の「商品名」（列27）をベース行の AD 列（0-based で29列目）にセットする。
    """
    df[32] = df[32].astype(str).str.strip()
    grouped = df.groupby(df[32], as_index=False, sort=False)
    output_rows = []
    for order_id, group in grouped:
        group = group.reset_index(drop=True)
        base_row = group.loc[0].copy()
        if len(group) > 1:
            base_row[28] = group.loc[1][26]
            base_row[29] = group.loc[1][27]
        else:
            base_row[28] = ""
            base_row[29] = ""
        output_rows.append(base_row)
    combined_df = pd.DataFrame(output_rows, columns=df.columns)
    return combined_df

# --- まとめたデータのうち、商品名の入力が必要な箇所をチェックする ---
def check_missing_product_names_combined(df):
    errors = []
    for idx, row in df.iterrows():
        order_id = row[32]
        if not (pd.notna(row[27]) and str(row[27]).strip()):
            errors.append({
                'order_id': order_id,
                'position': 'first',
                'row_index': idx
            })
        if pd.notna(row[28]) and str(row[28]).strip():
            if not (pd.notna(row[29]) and str(row[29]).strip()):
                errors.append({
                    'order_id': order_id,
                    'position': 'second',
                    'row_index': idx
                })
    return errors

def main():
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')

    if 'converted_df' not in st.session_state:
        st.session_state.converted_df = None

    uploaded_file = st.file_uploader(
        'CSVファイルをアップロードしてください',
        type=['csv'],
        help='Shift-JIS(cp932)エンコーディングのCSVファイル'
    )

    if uploaded_file:
        try:
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            
            # --- 発送先住所（例：列11）のスペース除去処理 ---
            if 11 in input_df.columns:
                input_df[11] = input_df[11].apply(
                    lambda x: x.replace(" ", "").replace("　", "") if isinstance(x, str) else x
                )
            
            st.success('ファイルの読み込みに成功しました。')
            st.write('【アップロードされたデータプレビュー（最初の3行）】')
            st.dataframe(input_df.head(3))
            
            # --- 商品数警告チェック ---
            product_warnings = check_product_count(input_df)
            if product_warnings:
                st.warning("以下の注文には3つ以上の商品が含まれています：")
                for warn in product_warnings:
                    st.write(f"注文ID: {warn['order_id']}　商品数: {warn['product_count']}　商品コード: {', '.join(warn['products'])}")
                st.write("---")
            
            combined_df = combine_rows_by_order_id_new(input_df)
            st.write('【受注ID統合後のデータプレビュー】')
            st.dataframe(combined_df.head(3))
            
            error_items = check_missing_product_names_combined(combined_df)
            if error_items:
                st.warning("以下の受注IDについて、商品名の入力が必要です。")
                with st.form("product_names_combined_form"):
                    for item in error_items:
                        order_id = item['order_id']
                        if item['position'] == 'first':
                            st.write(f"【受注ID: {order_id}】1つ目の商品名（列27）が空欄です。")
                            key = f"product_name_{order_id}_first"
                            st.text_input("商品名を入力してください", key=key)
                        elif item['position'] == 'second':
                            st.write(f"【受注ID: {order_id}】2つ目の商品名（列29）が空欄です。")
                            key = f"product_name_{order_id}_second"
                            st.text_input("商品名を入力してください", key=key)
                    submitted = st.form_submit_button("入力した商品名で更新")
                
                if submitted:
                    for item in error_items:
                        order_id = item['order_id']
                        row_idx = item['row_index']
                        if item['position'] == 'first':
                            key = f"product_name_{order_id}_first"
                            value = st.session_state.get(key, "").strip()
                            combined_df.at[row_idx, 27] = value
                        elif item['position'] == 'second':
                            key = f"product_name_{order_id}_second"
                            value = st.session_state.get(key, "").strip()
                            combined_df.at[row_idx, 29] = value
                    st.session_state.converted_df = combined_df
                    st.success("商品名の更新が完了しました！")
            else:
                st.session_state.converted_df = combined_df
                st.success("受注ID統合処理が完了しました。")
            
            if st.session_state.converted_df is not None:
                st.write("【変換後（統合＆商品名更新後）のデータプレビュー（最初の3行）】")
                st.dataframe(st.session_state.converted_df.head(3))
                
                csv_str = st.session_state.converted_df.to_csv(index=False, header=False, errors='ignore')
                csv_bytes = csv_str.encode('cp932')
                
                st.download_button(
                    label='変換済みCSVをダウンロード',
                    data=csv_bytes,
                    file_name='hatabarai_output.csv',
                    mime='application/octet-stream'
                )
                
                if st.button('新しい変換を開始'):
                    for key in ['converted_df']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.experimental_rerun()
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')

if __name__ == '__main__':
    main()
