def convert_to_hatabarai(input_df):
    """CSVデータを発払い形式に変換する関数"""
    try:
        # セッションステートの初期化
        if 'conversion_state' not in st.session_state:
            st.session_state.conversion_state = 'initial'
            st.session_state.error_items = []
            st.session_state.product_names = {}
            st.session_state.result_rows = []

        # 初期状態での処理
        if st.session_state.conversion_state == 'initial':
            order_id_col = input_df.columns[32]
            grouped = input_df.groupby(input_df[order_id_col])
            
            for order_id, group in grouped:
                row = [""] * len(input_df.columns)
                first_row = group.iloc[0]
                
                # 基本情報の転記
                for i in range(len(input_df.columns)):
                    if pd.notna(first_row[i]):
                        row[i] = str(first_row[i]).strip()
                
                # 商品情報の処理
                has_error = False
                for i, (_, item) in enumerate(group.iterrows()):
                    product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                    product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                    
                    if not product_name or product_name == 'nan':
                        has_error = True
                        st.session_state.error_items.append({
                            'order_id': order_id,
                            'product_code': product_code,
                            'index': i,
                            'row': row.copy()
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
                
                if not has_error:
                    st.session_state.result_rows.append(row)
            
            if st.session_state.error_items:
                st.session_state.conversion_state = 'need_input'
            else:
                st.session_state.conversion_state = 'complete'

        # 商品名入力が必要な場合の処理
        if st.session_state.conversion_state == 'need_input':
            st.warning("以下の商品について、商品名が空欄です。商品名を入力してください。")
            
            with st.form(key="product_names_form"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    for item in st.session_state.error_items:
                        key = f"product_name_{item['order_id']}_{item['product_code']}"
                        st.text_input(
                            f"商品名を入力（注文ID: {item['order_id']}, 商品コード: {item['product_code']}）",
                            key=key,
                            value=st.session_state.product_names.get(key, "")
                        )
                
                submitted = st.form_submit_button(
                    "入力した商品名で続行",
                    use_container_width=True,
                    type="primary"
                )
                
                if submitted:
                    # 入力値を保存
                    for item in st.session_state.error_items:
                        key = f"product_name_{item['order_id']}_{item['product_code']}"
                        value = st.session_state[key]
                        if value.strip():
                            st.session_state.product_names[key] = value
                    
                    # すべての入力が完了しているか確認
                    if len(st.session_state.product_names) == len(st.session_state.error_items):
                        # 入力された商品名でデータを更新
                        for item in st.session_state.error_items:
                            row = item['row']
                            key = f"product_name_{item['order_id']}_{item['product_code']}"
                            if item['index'] == 0:
                                row[27] = st.session_state.product_names[key]
                            elif item['index'] == 1:
                                row[29] = st.session_state.product_names[key]
                            st.session_state.result_rows.append(row)
                        
                        st.session_state.conversion_state = 'complete'
                    else:
                        st.error("すべての商品名を入力してください。")
                        return None

        # 変換完了時の処理
        if st.session_state.conversion_state == 'complete':
            if not st.session_state.result_rows:
                raise ValueError("変換結果が空です。入力データを確認してください。")
            
            # 結果のDataFrame作成
            result_df = pd.DataFrame(st.session_state.result_rows)
            
            # 1行目に空行を追加
            empty_row = [""] * len(input_df.columns)
            result_df = pd.concat([pd.DataFrame([empty_row]), result_df], ignore_index=True)
            
            # セッションステートをクリア
            st.session_state.conversion_state = 'initial'
            st.session_state.error_items = []
            st.session_state.product_names = {}
            st.session_state.result_rows = []
            
            return result_df
        
        return None
        
    except Exception as e:
        st.error(f"データ処理中にエラーが発生しました: {str(e)}")
        st.session_state.conversion_state = 'initial'
        return None
