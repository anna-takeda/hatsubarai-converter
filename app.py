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
    grouped = input_df.groupby(input_df.columns[32])
    result_rows = []
    
    for order_id, group in grouped:
        row = {}
        
        # 住所のスペース削除と処理（12列目）
        address = str(group.iloc[0, 11]).strip()
        if ',' in address:
            address = f'"{address}"'
        row['L'] = address
        
        # 商品名の処理（27列目）と数量（42列目）
        for i, (_, item) in enumerate(group.iterrows()):
            product_name = str(item.iloc[26]).strip()
            product_id = str(item.iloc[25])
            
            # 商品名の空欄チェック
            if not product_name or product_name == 'nan':
                raise ValueError(f"注文ID {order_id} の商品名が空欄です。商品IDは {product_id} です。")
            
            quantity = int(item.iloc[41])
            
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
        help='ANSIエンコーディングのCSVファイルを選択してください。'
    )
    
    if uploaded_file:
        try:
            # ファイル読み込み
            input_df = pd.read_csv(uploaded_file, encoding='ansi')
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
                    result_df.to_csv(output, encoding='ansi', index=False)
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
