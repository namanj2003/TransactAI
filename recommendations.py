def generate_recommendations(df_cat):
    recommendations = []
    category_spending = df_cat.groupby('category')['amount'].sum().sort_values(ascending=False)

    total_expenses = df_cat[df_cat['category'] != 'Income']['amount'].sum()
    total_income = df_cat[df_cat['category'] == 'Income']['amount'].sum()
    balance = total_income - total_expenses

    if total_expenses > 0.8 * total_income:
        recommendations.append({
            'type': 'warning',
            'title': 'High Spending Alert',
            'message': 'Your expenses are more than 80% of your income. Consider reviewing your discretionary spending.'
        })

    if 'Food' in category_spending and category_spending['Food'] > 0.2 * total_expenses:
        recommendations.append({
            'type': 'tip',
            'title': 'Food Expenses',
            'message': 'Food-related expenses are a significant part of your spending. Cooking at home or meal planning may help reduce costs.'
        })

    if 'Shopping' in category_spending and category_spending['Shopping'] > 0.15 * total_expenses:
        recommendations.append({
            'type': 'tip',
            'title': 'Shopping Habits',
            'message': 'Shopping expenses are relatively high. Consider tracking non-essential purchases.'
        })

    if balance > 0:
        recommendations.append({
            'type': 'success',
            'title': 'Positive Balance',
            'message': 'You have a positive net balance this period. Good job managing your finances!'
        })
    else:
        recommendations.append({
            'type': 'warning',
            'title': 'Negative Balance',
            'message': 'Your expenses exceed your income. Review your spending to avoid debt.'
        })

    if 'Cashback' in category_spending and category_spending['Cashback'] > 0:
        recommendations.append({
            'type': 'success',
            'title': 'Cashback Earned',
            'message': f'You earned Rs {category_spending["Cashback"]:,.2f} as cashback. Consider using more reward programs.'
        })

    return recommendations, category_spending
