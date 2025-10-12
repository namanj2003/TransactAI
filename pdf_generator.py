from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
import io

matplotlib.use('Agg')

def create_clean_pie_chart(category_spending, title="Spending Distribution"):
    threshold = 0.03
    total = category_spending.sum()
    main_categories = category_spending[category_spending / total >= threshold]
    small_categories = category_spending[category_spending / total < threshold]
    if len(small_categories) > 0:
        main_categories = pd.concat([
            main_categories,
            pd.Series([small_categories.sum()], index=['Others'])
        ])
    fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
    colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                   '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#95A5A6']
    wedges, texts, autotexts = ax.pie(
        main_categories.values,
        labels=main_categories.index,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
        startangle=90,
        colors=colors_list[:len(main_categories)],
        textprops={'fontsize': 10, 'weight': 'bold'},
        pctdistance=0.85
    )
    for text in texts:
        text.set_fontsize(11)
        text.set_weight('bold')
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_weight('bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    img_buffer.seek(0)
    plt.close()
    return img_buffer

def create_bar_chart(category_spending, title="Category-wise Spending"):
    top_categories = category_spending.nlargest(8)
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    bars = ax.barh(range(len(top_categories)), top_categories.values,
                   color='#4ECDC4', edgecolor='#2C3E50', linewidth=1.5)
    ax.set_yticks(range(len(top_categories)))
    ax.set_yticklabels(top_categories.index, fontsize=11)
    ax.set_xlabel('Amount (Rs)', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    for i, (bar, value) in enumerate(zip(bars, top_categories.values)):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height() / 2,
                f'Rs {value:,.0f}', ha='left', va='center',
                fontsize=9, fontweight='bold', color='#2C3E50')
    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    img_buffer.seek(0)
    plt.close()
    return img_buffer

def generate_expense_report(df_categorized, recommendations, category_spending, description_col='description'):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=1 * inch, bottomMargin=0.75 * inch)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c5f99'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("Expense Analysis Report", title_style))
    date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Executive Summary", heading_style))
    total_expenses = df_categorized[df_categorized['category'] != 'Income']['amount'].sum()
    total_income = df_categorized[df_categorized['category'] == 'Income']['amount'].sum()
    net_balance = total_income - total_expenses
    num_transactions = len(df_categorized)
    num_categories = df_categorized['category'].nunique()
    avg_confidence = df_categorized['confidence'].mean()
    summary_data = [
        ['Metric', 'Value'],
        ['Total Transactions', f"{num_transactions:,}"],
        ['Categories Detected', str(num_categories)],
        ['Total Expenses', f"Rs {total_expenses:,.2f}"],
        ['Total Income', f"Rs {total_income:,.2f}"],
        ['Net Balance', f"Rs {net_balance:,.2f}"],
        ['AI Confidence', f"{avg_confidence:.1%}"]
    ]
    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f99')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 25))
    elements.append(Paragraph("Category-wise Spending Breakdown", heading_style))
    category_data = [['Category', 'Amount', 'Count', '% of Total']]
    total_for_percentage = category_spending.sum()
    for category, amount in category_spending.items():
        count = len(df_categorized[df_categorized['category'] == category])
        percentage = (amount / total_for_percentage * 100) if total_for_percentage > 0 else 0
        category_data.append([
            category,
            f"Rs {amount:,.2f}",
            str(count),
            f"{percentage:.1f}%"
        ])
    category_table = Table(category_data, colWidths=[2 * inch, 1.8 * inch, 1 * inch, 1.2 * inch])
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f99')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    elements.append(category_table)
    elements.append(Spacer(1, 25))
    elements.append(Paragraph("Visual Analysis", heading_style))
    elements.append(Spacer(1, 10))
    if len(category_spending) > 0:
        chart_buffer = create_clean_pie_chart(category_spending)
        img = Image(chart_buffer, width=5 * inch, height=3.75 * inch)
        elements.append(img)
        elements.append(Spacer(1, 15))
        bar_buffer = create_bar_chart(category_spending)
        img_bar = Image(bar_buffer, width=5.5 * inch, height=3.4 * inch)
        elements.append(img_bar)
    elements.append(PageBreak())
    elements.append(Paragraph("Smart Recommendations & Insights", heading_style))
    elements.append(Spacer(1, 15))
    if recommendations:
        for rec in recommendations:
            if rec['type'] == 'warning':
                indicator = "[!]"
                rec_style = ParagraphStyle('Warning', parent=subheading_style, textColor=colors.HexColor('#e74c3c'))
            elif rec['type'] == 'success':
                indicator = "[+]"
                rec_style = ParagraphStyle('Success', parent=subheading_style, textColor=colors.HexColor('#27ae60'))
            elif rec['type'] == 'tip':
                indicator = "[*]"
                rec_style = ParagraphStyle('Tip', parent=subheading_style, textColor=colors.HexColor('#3498db'))
            else:
                indicator = "[i]"
                rec_style = subheading_style
            rec_title = Paragraph(f"{indicator} <b>{rec['title']}</b>", rec_style)
            elements.append(rec_title)
            message_text = rec['message'].replace('₹', 'Rs ')
            rec_message = Paragraph(message_text, styles['Normal'])
            elements.append(rec_message)
            elements.append(Spacer(1, 12))
    else:
        no_rec = Paragraph("No specific recommendations at this time.", styles['Normal'])
        elements.append(no_rec)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Top 10 Expenses", heading_style))
    elements.append(Spacer(1, 10))
    top_expenses = df_categorized[df_categorized['category'] != 'Income'].nlargest(10, 'amount')
    if len(top_expenses) > 0:
        top_data = [['#', 'Description', 'Category', 'Amount']]
        desc_col = description_col if description_col in top_expenses.columns else None
        if desc_col is None:
            for col in top_expenses.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['description', 'narration', 'particulars', 'details']):
                    desc_col = col
                    break
            if desc_col is None:
                for col in top_expenses.columns:
                    if top_expenses[col].dtype == 'object' and col not in ['category', 'transaction_type']:
                        desc_col = col
                        break
        for idx, (_, row) in enumerate(top_expenses.iterrows(), 1):
            if desc_col and desc_col in row.index:
                desc = str(row[desc_col])[:35] + '...' if len(str(row[desc_col])) > 35 else str(row[desc_col])
            else:
                desc = 'N/A'
            top_data.append([
                str(idx),
                desc,
                row['category'],
                f"Rs {row['amount']:,.2f}"
            ])
        top_table = Table(top_data, colWidths=[0.4 * inch, 2.8 * inch, 1.3 * inch, 1.5 * inch])
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f99')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(top_table)
    elements.append(Spacer(1, 30))
    footer_text = "Generated by TransactAI : AI-Powered Personal Expense Categorization System"
    footer = Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'],
                                                   fontSize=8, textColor=colors.grey, alignment=TA_CENTER))
    elements.append(footer)
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer
