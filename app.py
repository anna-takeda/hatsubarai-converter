def convert_to_hatabarai(input_df):
    try:
        # 初期化
        if 'error_items' not in st.session_state:
            st.session_state.error_items = []
            st.session_state.input_df = input_df
            st.session_state.submitted = False
            st.session_state.converted_df = None
            
            # エラーアイテムの収集
            order_id_col = input_df.columns[32]
            grouped = input_df.groupby(input_df[order_id_col])
            
            # 3つ以上の商品がある注文をチェック
            orders_with_many_items = []
            for order_id, group in grouped:
                if len(group) >= 3:
                    orders_with_many_items.append(order_id)
            
            # 警告表示
            if orders_with_many_items:
                warning_msg = "⚠️ 以下の注文には3つ以上の商品が含まれています（3つ目以降は処理されません）:\n"
                for order_id in orders_with_many_items:
                    warning_msg += f"- 注文ID: {order_id}\n"
                st.warning(warning_msg)
            
            # 既存の処理を継続
            for order_id, group in grouped:
                for i, (_, item) in enumerate(group.iterrows()):
                    if i >= 2:  # 3つ目以降はスキップ
                        continue
                    product_code = str(item[26]).strip() if pd.notna(item[26]) else ""
                    product_name = str(item[27]).strip() if pd.notna(item[27]) else ""
                    
                    if not product_name or product_name == 'nan':
                        st.session_state.error_items.append({
                            'order_id': order_id,
                            'product_code': product_code,
                            'index': i,
                            'row': [""] * len(input_df.columns)
                        })
                        # 以下は既存の処理と同じ
