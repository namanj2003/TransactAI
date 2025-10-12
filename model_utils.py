import torch
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification
import json
import streamlit as st
import re

@st.cache_resource
def load_model():
    try:
        model = DistilBertForSequenceClassification.from_pretrained("expense_model_distilbert")
        tokenizer = DistilBertTokenizerFast.from_pretrained("expense_model_distilbert")
        model.eval()
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device)
        with open('model_config.json', 'r') as f:
            config = json.load(f)
        return model, tokenizer, device, config
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None, None, None, None

def extract_transaction_features(description):
    desc_lower = str(description).lower()
    features = {
        'has_deposit_keyword': any(word in desc_lower for word in ['deposit', 'deposited', 'deposition', 'dep']),
        'has_cash_deposit': 'cash deposit' in desc_lower or 'deposit cash' in desc_lower,
        'has_cashback_keyword': any(word in desc_lower for word in ['cashback', 'cash back', 'reward', 'points']),
        'has_card_cashback': any(word in desc_lower for word in ['card cash back', 'millennia', 'cc cashback']),
        'has_credit_indicator': any(word in desc_lower for word in ['-cr', ' cr ', 'credit', 'credited', 'received', 'incoming']),
        'has_debit_indicator': any(word in desc_lower for word in ['-dr', ' dr ', 'debit', 'debited', 'paid', 'outgoing']),
        'is_neft': 'neft' in desc_lower,
        'is_imps': 'imps' in desc_lower,
        'is_rtgs': 'rtgs' in desc_lower,
        'is_upi': 'upi' in desc_lower or 'upi-' in desc_lower,
        'is_transfer': any(word in desc_lower for word in ['transfer', 'neft', 'imps', 'rtgs']),
        'has_card_keyword': any(word in desc_lower for word in ['card', 'visa', 'mastercard', 'rupay']),
        'is_emi': any(word in desc_lower for word in ['emi', 'loan', 'instalment', 'installment']),
        'is_bill_payment': any(word in desc_lower for word in ['cred', 'billpay', 'mobikwik', 'ccbp', 'bill payment']),
        'word_count': len(desc_lower.split()),
        'has_numbers': bool(re.search(r'\d', desc_lower)),
        'char_length': len(desc_lower)
    }
    return features

def predict_category_enhanced(description, model, tokenizer, device, id_map):
    if not description or str(description).strip() == '':
        return "Unknown", 0.0
    desc_str = str(description)
    features = extract_transaction_features(desc_str)
    inputs = tokenizer(
        desc_str,
        return_tensors='pt',
        padding='max_length',
        truncation=True,
        max_length=32
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)[0]
        predicted_idx = probs.argmax().item()
        confidence = probs[predicted_idx].item()
        category = id_map[str(predicted_idx)]
    desc_lower = desc_str.lower()
    if features['has_cash_deposit']:
        if features['has_credit_indicator'] or not features['has_debit_indicator']:
            return "Income", 0.98
    if category == "Cashback":
        if not (features['has_cashback_keyword'] or features['has_card_cashback']):
            if features['has_credit_indicator'] or features['has_deposit_keyword']:
                return "Income", 0.93
    elif category == "Income":
        if features['has_card_cashback'] or ('reward' in desc_lower and 'credit' in desc_lower):
            return "Cashback", 0.94
    if features['is_transfer']:
        if features['has_credit_indicator']:
            return "Income", 0.96
        elif features['has_debit_indicator']:
            return "Funds Transfer", 0.96
    if features['is_emi']:
        return "EMI", max(0.92, confidence)
    elif features['is_bill_payment']:
        return "Bill Payment", max(0.93, confidence)
    keyword_categories = {
        'Food': ['swiggy', 'zomato', 'dominos', 'pizza', 'kfc', 'mcdonalds', 'restaurant', 'food'],
        'Shopping': ['amazon', 'flipkart', 'myntra', 'ajio', 'shopping', 'mall'],
        'Travel': ['uber', 'ola', 'rapido', 'irctc', 'booking', 'hotel', 'flight'],
        'Entertainment': ['netflix', 'prime', 'hotstar', 'spotify', 'movie', 'cinema'],
        'Groceries': ['dmart', 'bigbasket', 'zepto', 'blinkit', 'grocery'],
        'Recharge': ['recharge', 'prepaid', 'jio', 'airtel', 'vi recharge'],
        'Utilities': ['electricity', 'water bill', 'gas bill', 'wifi', 'broadband'],
        'Healthcare': ['pharmacy', 'hospital', 'doctor', 'medical', 'medicine'],
        'Education': ['school', 'college', 'course', 'tuition', 'exam fee'],
        'Insurance': ['insurance', 'premium', 'policy', 'lic'],
        'Fees': ['charges', 'fee', 'annual charge', 'bank charges', 'penalty']
    }
    if confidence < 0.75:
        for cat, keywords in keyword_categories.items():
            if any(kw in desc_lower for kw in keywords):
                return cat, 0.87
    if confidence < 0.60:
        if 'upi-' in desc_lower or 'upi/' in desc_lower:
            if any(food in desc_lower for food in ['swiggy', 'zomato']):
                return "Food", 0.82
            elif any(shop in desc_lower for shop in ['amazon', 'flipkart']):
                return "Shopping", 0.82
        if features['has_debit_indicator']:
            return "Shopping", 0.70
        elif features['has_credit_indicator']:
            return "Income", 0.70
    return category, confidence

def predict_with_transaction_type(description, withdrawal_amount, deposit_amount, model, tokenizer, device, id_map):
    category, confidence = predict_category_enhanced(description, model, tokenizer, device, id_map)
    try:
        withdrawal = float(str(withdrawal_amount).replace(',', '')) if withdrawal_amount and str(
            withdrawal_amount).strip() not in ['', 'nan', 'None'] else 0
    except:
        withdrawal = 0
    try:
        deposit = float(str(deposit_amount).replace(',', '')) if deposit_amount and str(deposit_amount).strip() not in [
            '', 'nan', 'None'] else 0
    except:
        deposit = 0
    desc_lower = str(description).lower()
    if deposit > 0 and withdrawal == 0:
        if 'cash deposit' in desc_lower:
            return "Income", 0.99
        elif 'cashback' in desc_lower or 'cash back' in desc_lower or 'reward' in desc_lower:
            return "Cashback", 0.98
        elif any(word in desc_lower for word in ['neft-cr', 'imps-cr', 'rtgs-cr', 'salary', 'interest']):
            return "Income", 0.97
        elif category not in ['Income', 'Cashback']:
            return "Income", 0.88
    elif withdrawal > 0 and deposit == 0:
        if category == "Income" or category == "Cashback":
            if any(word in desc_lower for word in ['neft', 'imps', 'rtgs']):
                return "Funds Transfer", 0.90
            else:
                return "Shopping", 0.85
    return category, confidence

def predict_category(description, model, tokenizer, device, id_map):
    return predict_category_enhanced(description, model, tokenizer, device, id_map)
