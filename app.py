import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from model_utils import load_model, predict_category_enhanced, predict_with_transaction_type
from file_processors import process_csv_file, process_excel_file
from recommendations import generate_recommendations
from pdf_generator import generate_expense_report

st.set_page_config(
    page_title="TransactAI : Personal Expense Categorization",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
    <style>
    .main { padding: 0rem 1rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

def main():
    if 'reset_counter' not in st.session_state:
        st.session_state.reset_counter = 0

    st.title("💰 TransactAI : Personal Expense Categorization System")
    st.markdown("### AI-Powered Bank Statement Analysis")

    with st.spinner("Loading AI model..."):
        model, tokenizer, device, config = load_model()

    if model is None:
        st.error("❌ Model not found.")
        st.stop()

    st.success(f"✅ Model loaded on {device.upper()}")
    id_map = config['id_map']
    categories = config['categories']

    st.subheader("📁 Upload Bank Statement")
    uploaded_file = st.file_uploader(
        "Choose CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload bank statement in CSV or Excel format",
        key=f'file_uploader_{st.session_state.reset_counter}'
    )

    if uploaded_file is not None:
        if 'uploaded_file_name' not in st.session_state:
            st.session_state['uploaded_file_name'] = uploaded_file.name
        elif st.session_state['uploaded_file_name'] != uploaded_file.name:
            if 'categorized_df' in st.session_state:
                del st.session_state['categorized_df']
            if 'description_col' in st.session_state:
                del st.session_state['description_col']
            st.session_state['uploaded_file_name'] = uploaded_file.name

        file_extension = uploaded_file.name.split('.')[-1].lower()

        df = None
        description_col = None
        withdrawal_col = None
        deposit_col = None
        date_col = None

        if file_extension == 'csv':
            with st.spinner("Processing CSV..."):
                df, description_col, withdrawal_col, deposit_col, date_col = process_csv_file(uploaded_file)
        elif file_extension in ['xlsx', 'xls']:
            with st.spinner("Processing Excel..."):
                df, description_col, withdrawal_col, deposit_col, date_col = process_excel_file(uploaded_file)

        if df is not None and description_col:
            with st.expander("📋 Preview Data"):
                st.dataframe(df.head(10))

            st.markdown("---")
            st.subheader("🔧 Column Mapping")
            has_separate_columns = withdrawal_col is not None or deposit_col is not None

            if has_separate_columns:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    description_col = st.selectbox("Description", df.columns,
                        index=list(df.columns).index(description_col) if description_col in df.columns else 0)
                with col2:
                    withdrawal_options = [None] + list(df.columns)
                    withdrawal_idx = withdrawal_options.index(withdrawal_col) if withdrawal_col in withdrawal_options else 0
                    withdrawal_col = st.selectbox("Withdrawal/Debit", withdrawal_options, index=withdrawal_idx)
                with col3:
                    deposit_options = [None] + list(df.columns)
                    deposit_idx = deposit_options.index(deposit_col) if deposit_col in deposit_options else 0
                    deposit_col = st.selectbox("Deposit/Credit", deposit_options, index=deposit_idx)
                with col4:
                    date_options = [None] + list(df.columns)
                    date_idx = date_options.index(date_col) if date_col in date_options else 0
                    date_col = st.selectbox("Date", date_options, index=date_idx)
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    description_col = st.selectbox("Description", df.columns,
                        index=list(df.columns).index(description_col) if description_col in df.columns else 0)
                with col2:
                    amount_options = [None] + list(df.columns)
                    amount_idx = 0
                    amount_col = st.selectbox("Amount", amount_options, index=amount_idx)
                with col3:
                    date_options = [None] + list(df.columns)
                    date_idx = date_options.index(date_col) if date_col in date_options else 0
                    date_col = st.selectbox("Date", date_options, index=date_idx)

            st.markdown("---")
            if st.button("🚀 Categorize Transactions", type="primary", use_container_width=True):
                with st.spinner("Categorizing with AI..."):
                    categories_pred = []
                    confidences = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for idx, row in df.iterrows():
                        desc = row[description_col]
                        if withdrawal_col and deposit_col:
                            withdrawal = row[withdrawal_col] if pd.notna(row[withdrawal_col]) else 0
                            deposit = row[deposit_col] if pd.notna(row[deposit_col]) else 0
                            category, confidence = predict_with_transaction_type(
                                desc, withdrawal, deposit, model, tokenizer, device, id_map
                            )
                        else:
                            category, confidence = predict_category_enhanced(
                                desc, model, tokenizer, device, id_map
                            )
                        categories_pred.append(category)
                        confidences.append(confidence)
                        progress = (idx + 1) / len(df)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing: {idx + 1}/{len(df)}")

                    df['category'] = categories_pred
                    df['confidence'] = confidences

                    def safe_convert_amount(value):
                        if pd.isna(value):
                            return 0.0
                        val_str = str(value).strip()
                        if '*' in val_str or val_str == '':
                            return 0.0
                        try:
                            cleaned = val_str.replace(',', '').replace('₹', '').replace('Rs', '')
                            return abs(float(cleaned))
                        except:
                            return 0.0

                    if withdrawal_col and deposit_col:
                        df['amount'] = df.apply(lambda row:
                            safe_convert_amount(row[withdrawal_col]) + safe_convert_amount(row[deposit_col]), axis=1)
                        df['transaction_type'] = df.apply(lambda row:
                            'Expense' if safe_convert_amount(row[withdrawal_col]) > 0 else 'Income', axis=1)
                    elif withdrawal_col:
                        df['amount'] = df[withdrawal_col].apply(safe_convert_amount)
                        df['transaction_type'] = 'Expense'
                    elif deposit_col:
                        df['amount'] = df[deposit_col].apply(safe_convert_amount)
                        df['transaction_type'] = 'Income'
                    else:
                        df['amount'] = 0
                        df['transaction_type'] = 'Unknown'

                    st.session_state['categorized_df'] = df
                    st.session_state['description_col'] = description_col

                    st.success("✅ Complete!")
                    st.balloons()

            if 'categorized_df' in st.session_state:
                df_cat = st.session_state['categorized_df']
                st.markdown("---")
                st.subheader("📊 Results")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Transactions", len(df_cat))
                col2.metric("Categories", df_cat['category'].nunique())
                col3.metric("Avg Confidence", f"{df_cat['confidence'].mean():.1%}")
                col4.metric("Total", f"₹{df_cat['amount'].sum():,.0f}")

                tab1, tab2, tab3 = st.tabs(["📋 Data", "📊 Charts", "🎯 Insights"])
                with tab1:
                    display_cols = [st.session_state['description_col'], 'category', 'amount', 'confidence']
                    display_df = df_cat[display_cols].copy()
                    display_df['confidence'] = display_df['confidence'].apply(lambda x: f"{x:.1%}")
                    display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(display_df, use_container_width=True, height=400)
                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        category_counts = df_cat['category'].value_counts()
                        fig = px.pie(values=category_counts.values, names=category_counts.index,
                                     title="Transaction Distribution")
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        if df_cat['amount'].sum() > 0:
                            cat_amt = df_cat.groupby('category')['amount'].sum().sort_values()
                            fig = px.bar(x=cat_amt.values, y=cat_amt.index, orientation='h',
                                         title="Spending by Category", labels={'x': '₹', 'y': ''})
                            st.plotly_chart(fig, use_container_width=True)
                    if df_cat['amount'].sum() > 0:
                        st.markdown("### 💸 Top 10 Expenses")
                        top = df_cat[df_cat['category'] != 'Income'].nlargest(10, 'amount')
                        if len(top) > 0:
                            top_display = top[[st.session_state['description_col'], 'category', 'amount']].copy()
                            top_display['amount'] = top_display['amount'].apply(lambda x: f"₹{x:,.2f}")
                            st.dataframe(top_display, use_container_width=True, hide_index=True)
                with tab3:
                    recommendations, category_spending = generate_recommendations(df_cat)
                    if recommendations:
                        for rec in recommendations:
                            if rec['type'] == 'warning':
                                st.warning(f"⚠️ **{rec['title']}**\n\n{rec['message']}")
                            elif rec['type'] == 'success':
                                st.success(f"✅ **{rec['title']}**\n\n{rec['message']}")
                            elif rec['type'] == 'tip':
                                st.info(f"💡 **{rec['title']}**\n\n{rec['message']}")
                            else:
                                st.info(f"ℹ️ **{rec['title']}**\n\n{rec['message']}")
                    st.markdown("---")
                    st.markdown("### 📈 Summary")
                    col1, col2, col3 = st.columns(3)
                    expenses = df_cat[df_cat['category'] != 'Income']['amount'].sum()
                    income = df_cat[df_cat['category'] == 'Income']['amount'].sum()
                    balance = income - expenses
                    col1.metric("Expenses", f"₹{expenses:,.2f}")
                    col2.metric("Income", f"₹{income:,.2f}")
                    col3.metric("Balance", f"₹{balance:,.2f}")
                st.markdown("---")
                st.subheader("💾 Export")
                col1, col2 = st.columns(2)
                with col1:
                    csv = df_cat.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                with col2:
                    recs, cat_spend = generate_recommendations(df_cat)
                    desc_col_name = st.session_state.get('description_col', 'description')
                    pdf_buffer = generate_expense_report(df_cat, recs, cat_spend, desc_col_name)
                    st.download_button(
                        "📄 Download PDF Report",
                        pdf_buffer,
                        f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        "application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🔄 Upload New File", use_container_width=True, type="secondary",
                                 key=f'reset_btn_{st.session_state.reset_counter}'):
                        st.session_state.reset_counter += 1
                        keys_to_keep = ['reset_counter']
                        for key in list(st.session_state.keys()):
                            if key not in keys_to_keep:
                                del st.session_state[key]
                        st.rerun()

if __name__ == "__main__":
    main()
