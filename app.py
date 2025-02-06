def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    # まず、33列目（インデックス32）の注文IDを確認
    st.write("データの形状:", input_df.shape)
    
    try:
        # セッションステートの初期化
        if 'error_items' not in st.session_state:
            st.session_state.error_items = []
        if 'product_names' not in st.session_state:
            st.session_state.product_names = {}
        
        # 注文IDで行をグループ化（CSVの見た目の33列目の注文番号、インデックスは32）
        order_id_col = input_df.columns[32]  # 33列目のカラム名を取得
        grouped = input_df.groupby(input_df[order_id_col])
        
        result_rows = []
        
        # 初回実行時のみエラーアイテムを収集
        if not st.session_state.error_items:
            for order_id, group in grouped:
                # 42列分の空の配列を作成
                row = [""] * len(input_df.columns)
                
                # 基本情報を転記
                first_row = group.iloc[0]
                for i in range(len(input_df.columns)):
                    if pd.notna(first_row[i]):  # null値でない場合のみ値を設定
                        row[i] = str(first_row[i]).strip()
                
                # 商品情報の処理
                for i, (_, item) in enumerate(group.iterrows()):
                    product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                    product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                    
                    # 商品名の空欄チェック
                    if not product_name or product_name == 'nan':
                        st.session_state.error_items.append({
                            'order_id': order_id,
                            'product_code': product_code,
                            'index': i,
                            'row': row.copy()  # 現在の行データをコピー
                        })
                        continue
                    
                    if i == 0:
                        row[26] = product_code
                        row[27] = product_name
                    elif i == 1:
                        row[28] = product_code
                        row[29] = product_name
                    elif i > 1:
                        raise ValueError(f"受注ID {order_id} に3つ以上の商品が含まれています。")
                
                if not any(err['order_id'] == order_id for err in st.session_state.error_items):
                    result_rows.append(row)
        
        # エラーアイテムの処理
        if st.session_state.error_items:
            st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
            
            # フォームを使用して入力を管理
            with st.form("product_names_form"):
                # エラーのある商品ごとに入力フィールドを表示
                for item in st.session_state.error_items:
                    st.write(f"注文ID: {item['order_id']}, 商品コード: {item['product_code']}")
                    key = f"product_name_{item['order_id']}_{item['product_code']}"
                    input_value = st.text_input(
                        f"商品名を入力",
                        key=key,
                        value=st.session_state.product_names.get(key, "")
                    )
                    st.session_state.product_names[key] = input_value
                
                # フォームのサブミットボタン
                submitted = st.form_submit_button("入力した商品名で続行")
                if submitted:
                    # すべての商品名が入力されているか確認
                    all_filled = all(value.strip() != "" for value in st.session_state.product_names.values())
                    
                    if all_filled:
                        # 入力された商品名を使用してresult_rowsを更新
                        for item in st.session_state.error_items:
                            row = item['row']
                            key = f"product_name_{item['order_id']}_{item['product_code']}"
                            if item['index'] == 0:
                                row[27] = st.session_state.product_names[key]
                            elif item['index'] == 1:
                                row[29] = st.session_state.product_names[key]
                            result_rows.append(row)
                        
                        # セッションステートをクリア
                        st.session_state.error_items = []
                        st.session_state.product_names = {}
                    else:
                        st.error("すべての商品名を入力してください。")
                        return None
            
            if not submitted:
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
