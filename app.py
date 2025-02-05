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
    # デバッグ用の出力
    st.write("データの形状:", input_df.shape)
    st.write("32列目（注文ID）のユニーク値:", input_df[31].unique())
    
    # 受注IDでグループ化（32列目の注文ID）
    grouped = input_df.groupby(31)
    st.write("グループ数:", len(grouped))
    
    result_rows = []
    
    for order_id, group in grouped:
        # デバッグ用の出力
        st.write(f"処理中の注文ID: {order_id}, グループの行数: {len(group)}")
        
        # 42列すべての情報を保持する配列を作成
        row = [""] * 42
        
        # 基本情報の転記（最初の行のデータを使用）
        first_row = group.iloc[0]
        
        # すべての列の情報を保持
        for i in range(42):
            if i not in [26, 27]:  # 商品コードと商品名以外はそのまま保持
                row[i] = str(first_row[i]).strip() if pd.notna(first_row[i]) else ""
        
        # 商品情報の処理
        for i, (_, item) in enumerate(group.iterrows()):
            product_code = str(item[26]).strip()  # 商品コード
            product_name = str(item[27]).strip()  # 商品名
            quantity = int(item[41])  # 数量

            # 商品名の空欄チェック
            if not product_name or product_name == 'nan':
                raise ValueError(f"注文ID {order_id} の商品名が空欄です。商品コードは {product_code} です。")
            
            # 数量に応じた商品名の形式設定
            if quantity >= 2:
                product_name = f"{quantity}★{product_name}"
            
            if i == 0:
                # 1つ目の商品は27列目（28番目）に配置
                row[26] = product_code
                row[27] = product_name
            elif i == 1:
                # 2つ目の商品は29列目（30番目）に配置
                row[28] = product_code
                row[29] = product_name
            elif i > 1:
                raise ValueError(f"受注ID {order_id} に3つ以上の商品が含まれています。")
        
        result_rows.append(row)
    
    # デバッグ用の出力
    st.write("処理した行数:", len(result_rows))
    
    # 結果のDataFrame作成（列名なし）
    if result_rows:  # 結果がある場合のみDataFrame作成
        result_df = pd.DataFrame(result_rows)
        
        # 1行目に完全な空行を追加
        empty_row = [""] * 42
        result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
        
        return result_df
    else:
        st.error("変換結果が空です。データを確認してください。")
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
                    
                except ValueError as e:
                    st.error(f'⚠️ エラーが発生しました: {str(e)}')
                except Exception as e:
                    st.error(f'⚠️ 予期せぬエラーが発生しました: {str(e)}')
                    
        except Exception as e:
            st.error(f'⚠️ CSVファイルの読み込みに失敗しました: {str(e)}')

if __name__ == '__main__':
    main()
