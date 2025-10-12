import pandas as pd
import streamlit as st

def process_csv_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        description_col = None
        withdrawal_col = None
        deposit_col = None
        date_col = None

        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['description', 'particulars', 'narration', 'details', 'transaction', 'remark']):
                if description_col is None:
                    description_col = col
            elif any(keyword in col_lower for keyword in ['withdrawal', 'debit', 'withdraw', 'dr', 'spent']):
                if withdrawal_col is None:
                    withdrawal_col = col
            elif any(keyword in col_lower for keyword in ['deposit', 'credit', 'cr', 'received']):
                if deposit_col is None:
                    deposit_col = col
            elif any(keyword in col_lower for keyword in ['date', 'transaction date', 'value date', 'txn date']):
                if date_col is None:
                    date_col = col

        if description_col is None:
            description_col = df.columns[0]
        return df, description_col, withdrawal_col, deposit_col, date_col

    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        return None, None, None, None, None

def process_excel_file(uploaded_file):
    try:
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        except:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, engine='xlrd')

        header_row = None
        for idx in range(min(50, len(df))):
            row = df.iloc[idx]
            row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
            if any(date_word in row_str for date_word in ['date', 'txn date', 'trans date', 'posting date']):
                if any(desc_word in row_str for desc_word in ['narration', 'description', 'particulars', 'details', 'transaction']):
                    header_row = idx
                    break

        if header_row is not None:
            new_columns = []
            col_counter = {}
            for col in df.iloc[header_row]:
                col_str = str(col).strip()
                if pd.isna(col) or col_str == '' or col_str.lower() == 'nan':
                    col_str = f'Unnamed_{len(new_columns)}'
                if col_str in col_counter:
                    col_counter[col_str] += 1
                    col_str = f"{col_str}_{col_counter[col_str]}"
                else:
                    col_counter[col_str] = 0
                new_columns.append(col_str)
            df.columns = new_columns
            df = df.iloc[header_row + 1:].reset_index(drop=True)

        def is_definitely_not_transaction(row):
            text_vals = [str(val).lower() for val in row if pd.notna(val)]
            if len(text_vals) == 0:
                return True
            text_str = ' '.join(text_vals)
            definite_bad = [
                'statement summary', 'end of statement',
                'opening balance as on', 'closing balance as on',
                'opening balance','closing balance',
                'page no', 'branch address', 'registered office',
                'account number:', 'customer id:', 'ifsc code:',
                'swift code:', 'micr code:', 'email id:',
                'joint holder', 'nomination:', 'scheme:',
                'communication address', 'regd. mobile',
                'effective available balance', 'date of issue',
                'grand total', 'generated on:', 'branch code'
            ]
            return any(keyword in text_str for keyword in definite_bad)

        df = df[~df.apply(is_definitely_not_transaction, axis=1)]
        df = df.dropna(how='all')
        df = df.reset_index(drop=True)

        description_col = None
        withdrawal_col = None
        deposit_col = None
        date_col = None

        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'unnamed' in col_lower:
                continue
            if any(keyword in col_lower for keyword in ['narration', 'description', 'particulars', 'details', 'transaction']):
                if description_col is None:
                    description_col = col
            elif any(keyword in col_lower for keyword in ['withdrawal', 'debit', 'withdraw', 'dr', 'paid']):
                if 'cheque' not in col_lower and 'ref' not in col_lower:
                    if withdrawal_col is None:
                        withdrawal_col = col
            elif any(keyword in col_lower for keyword in ['deposit', 'credit', 'cr', 'received']):
                if deposit_col is None:
                    deposit_col = col
            elif any(keyword in col_lower for keyword in ['date', 'transaction date', 'value date', 'txn date', 'posting']):
                if 'from' not in col_lower and 'to' not in col_lower:
                    if date_col is None:
                        date_col = col

        if description_col and description_col in df.columns:
            df = df[df[description_col].notna()]
            df = df[df[description_col].astype(str).str.strip() != '']
            df = df[df[description_col].astype(str).str.len() > 1]
            df = df[df[description_col].apply(lambda x: str(x).count('*') < len(str(x)) * 0.8)]

        if withdrawal_col and withdrawal_col in df.columns:
            df = df[~df[withdrawal_col].apply(lambda x: pd.notna(x) and ('*' in str(x) or str(x).strip() == ''))]
        if deposit_col and deposit_col in df.columns:
            df = df[~df[deposit_col].apply(lambda x: pd.notna(x) and ('*' in str(x) or str(x).strip() == ''))]
        df = df.drop_duplicates(keep='first')
        df = df.reset_index(drop=True)

        return df, description_col, withdrawal_col, deposit_col, date_col

    except Exception as e:
        st.error(f"Error processing Excel: {str(e)}")
        return None, None, None, None, None
