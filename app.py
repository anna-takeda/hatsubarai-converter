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
    # 受注ID（列32）の前後空白を除去
    df[32] = df[32].astype(str).str.strip()
    # 元の順序を保持するため sort=False
    grouped = df.groupby(df[32], as_index=False, sort=False)
    output_rows = []
    for order_id, group in grouped:
        group = group.reset_index(drop=True)
        base_row = group.loc[0].copy()
        if len(group) > 1:
            base_row[28] = group.loc[1][26]   # 2行目の商品ID → AC列 (0-based 28)
            base_row[29] = group.loc[1][27]   # 2行目の商品名 → AD列 (0-based 29)
        else:
            base_row[28] = ""
            base_row[29] = ""
        output_rows.append(base_row)
    # インデックスをリセットして連番にする
    combined_df = pd.DataFrame(output_rows, columns=df.columns).reset_index(drop=True)
    return combined_df

# --- まとめたデータのうち、商品名の入力が必要な箇所をチェックする ---
def check_missing_product_names_combined(df):
    """
    まとめた後の DataFrame について、
      - 1つ目の商品名（列27）が空欄ならエラーとし、対応する商品ID（列26）も返す。
      - もし2つ目の商品が存在する（AC列＝28が空でない）場合、2つ目の商品名（列29）が空欄ならエラーとし、対応する商品ID（列28）も返す。
    各エラー項目は、{'order_id':…, 'position': 'first' or 'second', 'row_index': …, 'product_id': …} の形式とする。
    """
    errors = []
    for idx, row in df.iterrows():
        order_id = row[32]
        # 1つ目の商品名：列27（対応する商品ID：列26）
        if not (pd.notna(row[27]) and str(row[27]).strip()):
            errors.append({
                'order_id': order_id,
                'position': 'first',
                'row_index': idx,
                'product_id': row[26] if pd.notna(row[26]) else ""
            })
        # 2つ目の商品が存在するかどうかは、AC列（28）が空でないかで判断
        if pd.notna(row[28]) and str(row[28]).strip():
            if not (pd.notna(row[29]) and str(row[29]).strip()):
                errors.append({
                    'order_id': order_id,
                    'position': 'second',
                    'row_index': idx,
                    'product_id': row[28]
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
            # CSV読み込み（エンコーディング cp932、ヘッダーなし）
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            
            # --- 発送先住所（例：列11）のスペース除去処理（必要に応じて列番号を調整） ---
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
            
            # 受注IDごとに行をまとめる
            combined_df = combine_rows_by_order_id_new(input_df)
            st.write('【受注ID統合後のデータプレビュー】')
            st.dataframe(combined_df.head(3))
            
            # 欠損している商品名のチェック（エラー項目に商品IDも含める）
            error_items = check_missing_product_names_combined(combined_df)
            if error_items:
                st.warning("以下の受注IDについて、商品名の入力が必要です。")
                with st.form("product_names_combined_form"):
                    for item in error_items:
                        order_id = item['order_id']
                        product_id = item['product_id']
                        if item['position'] == 'first':
                            st.write(f"【受注ID: {order_id}】【商品ID: {product_id}】1つ目の商品名（列27）が空欄です。")
                            key = f"product_name_{order_id}_first"
                            st.text_input("商品名を入力してください", key=key)
                        elif item['position'] == 'second':
                            st.write(f"【受注ID: {order_id}】【商品ID: {product_id}】2つ目の商品名（列29）が空欄です。")
                            key = f"product_name_{order_id}_second"
                            st.text_input("商品名を入力してください", key=key)
                    submitted = st.form_submit_button("入力した商品名で更新")
                
                if submitted:
                    for item in error_items:
                        order_id = item['order_id']
                        idx = item['row_index']
                        if item['position'] == 'first':
                            key = f"product_name_{order_id}_first"
                            if key in st.session_state and st.session_state[key].strip():
                                value = st.session_state[key].strip()
                                # 1つ目の商品名は 0-based で 27 列目に更新
                                combined_df.loc[idx, 27] = value
                        elif item['position'] == 'second':
                            key = f"product_name_{order_id}_second"
                            if key in st.session_state and st.session_state[key].strip():
                                value = st.session_state[key].strip()
                                # 2つ目の商品名は 0-based で 29 列目に更新
                                combined_df.loc[idx, 29] = value
                    st.session_state.converted_df = combined_df
                    st.success("商品名の更新が完了しました！")
            else:
                st.session_state.converted_df = combined_df
                st.success("受注ID統合処理が完了しました。")
            
            # --- 変換結果のダウンロード ---
            if st.session_state.converted_df is not None:
                st.write("【変換後（統合＆商品名更新後）のデータプレビュー（最初の3行）】")
                st.dataframe(st.session_state.converted_df.head(3))
                
                # 先頭行を空欄にするための DataFrame を作成
                empty_row = pd.DataFrame([[""] * st.session_state.converted_df.shape[1]], columns=st.session_state.converted_df.columns)
                final_df = pd.concat([empty_row, st.session_state.converted_df], ignore_index=True)
                
                csv_str = final_df.to_csv(index=False, header=False, errors='ignore')
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
