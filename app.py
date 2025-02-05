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
    # 受注IDでグループ化（33列目の注文番号）
    grouped = input_df.groupby(32)  # インデックスで列を指定
    result_rows = []
    
    for order_id, group in grouped:
        row = {}
        
        # 基本情報の転記（最初の行のデータを使用）
        first_row = group.iloc[0]
        
        # 文字列として取り込んで先頭の0を保持
        row['A'] = str(first_row[8])  # 電話番号
        row['B'] = str(first_row[10])  # 郵便番号
        row['C'] = str(first_row[15]).strip()  # 名前
        row['D'] = str(first_row[16]).strip()  # カナ名
        row['E'] = str(first_row[19])  # 会社コード
        row['F'] = str(first_row[21])  # 会社郵便番号
        row['G'] = str(first_row[22]).strip()  # 会社住所
        row['H'] = str(first_row[24])  # 会社名
        row['I'] = str(first_row[4])  # 依頼日
        row['J'] = str(first_row[5])  # 希望配達日
        row['K'] = str(first_row[6])  # 時間帯コード
        row['L'] = str(first_row[11]).strip()  # 住所

        # カンマを含む住所の処理
        if ',' in row['L']:
            row['L'] = f'"{row["L"]}"'
        
        # 商品名の処理（27列目）と数量（42列目）
        for i, (_, item) in enumerate(group.iterrows()):
            product_name = str(item[26]).strip()
            product_id = str(item[25])
            
            # 商品名の空欄チェック
            if not product_name or product_name == 'nan':
                raise ValueError(f"注文ID {order_id} の商品名が空欄です。商品IDは {product_id} です。")
            
            quantity = int(item[41])
            
            # 数量に応じた商品名の形式設定
            if quantity >= 2:
                product_name = f"{quantity}★{product_name}"
            
            # 商品名を適切な列に配置
            if i == 0:
                row['AB'] = product_name
            elif i == 1:
                row['AD'] = product_name
            elif i > 1:
                raise ValueError(f"受注ID {order_id} に3つ以上の商品が含まれています。")
        
        result_rows.append(row)
    
    # 結果のDataFrame作成
    result_df = pd.DataFrame(result_rows)
    
    # 列の順序を指定
    column_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'AB', 'AD']
    result_df = result_df.reindex(columns=column_order)
    
    # 1行目に空行を追加
    result_df = pd.concat([pd.DataFrame([{}]), result_df], ignore_index=True)
    
    return result_df

def main():
    st.title('発払いCSV変換ツール')
    st.write('ヤマトB2のCSVファイルを発払い形式に変換します。')
    
    # ファイルアップロード部分
    uploaded_file = st.file_uploader(
        'CSVファイルをアップロードしてください',
        type=['csv'],
        help='Shift-JISエンコーディングのCSVファイルを選択してください。'
    )
    
    if uploaded_file:
        try:
            # ヘッダーなしで読み込み、数値を文字列として扱う
            input_df = pd.read_csv(uploaded_file, encoding='cp932', dtype=str, header=None)
            st.success('ファイルの読み込みに成功しました。')
            
            # データの簡単なプレビュー表示
            st.write('データプレビュー（最初の3行）:')
            st.dataframe(input_df.head(3))
            
            # 変換ボタン
            if st.button('変換開始', type='primary'):
                try:
                    with st.spinner('変換処理中...'):
                        result_df = convert_to_hatabarai(input_df)
                    
                    # 変換結果をCSVとして出力
                    output = io.BytesIO()
                    result_df.to_csv(output, encoding='cp932', index=False, float_format=None)
                    output.seek(0)
                    
                    # ダウンロードボタン表示
                    st.download_button(
                        label='変換済みCSVをダウンロード',
                        data=output,
                        file_name='hatabarai_output.csv',
                        mime='text/csv'
                    )
                    
                    st.success('✨ 変換が完了しました！')
                    
                except ValueError as e:
                    st.error(f'⚠️ エラーが発生しました: {str(e)}')
                except Exception as e:
                    st.error(f'⚠️ 予期せぬエラーが発生しました: {str(e)}')
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')
    
    # 使い方の説明
    with st.expander('使い方'):
        st.write('''
        1. 「ファイルを選択」ボタンをクリックしてCSVファイルをアップロード
        2. データプレビューを確認
        3. 「変換開始」ボタンをクリック
        4. 変換完了後、「変換済みCSVをダウンロード」ボタンからファイルをダウンロード
        ''')

if __name__ == '__main__':
    main()
