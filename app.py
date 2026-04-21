"""
Finanz Guru Local - Persönliche Finanzverwaltung
Design: Clean Banking — navy sidebar, tinted metric cards, professional German UI
"""
import html
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

from db import init_db, insert_transactions, get_transactions, get_budgets, upsert_budget, get_monthly_summary, update_category
from parser_db import parse_db_pdf
from categorizer import categorize_transactions, CATEGORIES, update_rule, get_rules

st.set_page_config(
    page_title="Finanz Guru Local",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# STYLING - Clean Banking theme
# ============================================================
st.markdown("""
<style>
    /* Base */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Sidebar — navy */
    section[data-testid="stSidebar"] {
        background-color: #1e3a5f !important;
        border-right: none;
    }
    section[data-testid="stSidebar"] * {
        color: #cbd5e1 !important;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 0.45rem 0.75rem;
        border-radius: 7px;
        margin-bottom: 0.2rem;
        color: #cbd5e1 !important;
        transition: background 0.12s;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background-color: rgba(59,130,246,0.15) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label[aria-checked="true"] {
        background-color: rgba(59,130,246,0.22) !important;
        color: #93c5fd !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaption"] {
        color: #94a3b8 !important;
    }

    /* Headings */
    h1 {
        font-weight: 700;
        color: #111827;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        font-weight: 600;
        color: #1f2937;
        letter-spacing: -0.01em;
    }

    /* Tinted metric cards */
    .metric-card {
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .metric-card-income {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
    }
    .metric-card-expense {
        background: #fef2f2;
        border: 1px solid #fecaca;
    }
    .metric-card-balance-pos {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }
    .metric-card-balance-neg {
        background: #fff7ed;
        border: 1px solid #fed7aa;
    }
    .metric-card-count {
        background: #faf5ff;
        border: 1px solid #e9d5ff;
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.4rem;
        color: #6b7280;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.15;
        letter-spacing: -0.02em;
    }
    .metric-sub {
        font-size: 0.75rem;
        margin-top: 0.5rem;
    }
    .metric-card-income .metric-value  { color: #15803d; }
    .metric-card-income .metric-label  { color: #166534; }
    .metric-card-expense .metric-value { color: #dc2626; }
    .metric-card-expense .metric-label { color: #991b1b; }
    .metric-card-balance-pos .metric-value { color: #1d4ed8; }
    .metric-card-balance-pos .metric-label { color: #1e40af; }
    .metric-card-balance-neg .metric-value { color: #c2410c; }
    .metric-card-balance-neg .metric-label { color: #9a3412; }
    .metric-card-count .metric-value { color: #7c3aed; }
    .metric-card-count .metric-label { color: #6d28d9; }

    /* Trend badge */
    .trend-badge {
        display: inline-block;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 0.35rem;
    }
    .trend-up   { background: #dcfce7; color: #166534; }
    .trend-down { background: #fee2e2; color: #991b1b; }
    .trend-info { background: #dbeafe; color: #1e40af; }
    .trend-neu  { background: #f3f4f6; color: #6b7280; }

    /* Panel */
    .panel {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 1.25rem;
    }

    /* Filter toolbar */
    .filter-toolbar {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.15s;
        border: 1px solid #e2e8f0;
    }
    .stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
    }
    .stButton > button[kind="primary"] {
        background: #3b82f6;
        border: none;
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2563eb;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 7px 7px 0 0; padding: 0.45rem 1rem; }

    /* DataFrame */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
    [data-testid="stAlert"]     { border-radius: 10px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }

    /* Status pills */
    .status-pill {
        display: inline-block;
        padding: 0.18rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .status-ok   { background: #dcfce7; color: #166534; }
    .status-warn { background: #fef3c7; color: #92400e; }
    .status-over { background: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# Inițializare DB
init_db()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
CATEGORY_BADGE_COLORS = {
    'Einkommen':         ('#dcfce7', '#166534'),
    'Lebensmittel':      ('#fef3c7', '#92400e'),
    'Transport':         ('#e0f2fe', '#0369a1'),
    'Wohnen':            ('#fce7f3', '#9d174d'),
    'Energie':           ('#fff7ed', '#9a3412'),
    'Abos & Streaming':  ('#f0f9ff', '#0c4a6e'),
    'Gastronomie':       ('#fdf4ff', '#7e22ce'),
    'Versicherung':      ('#f0fdf4', '#14532d'),
    'Gesundheit':        ('#fef2f2', '#7f1d1d'),
    'Bank & Gebühren':   ('#f1f5f9', '#1e293b'),
    'Online Shopping':   ('#fff1f2', '#9f1239'),
    'Kleidung':          ('#faf5ff', '#581c87'),
    'Elektronik':        ('#eff6ff', '#1e3a8a'),
    'Haushalt':          ('#f0fdf4', '#166534'),
    'Telekom & Internet':('#ecfeff', '#164e63'),
    'Steuern & Abgaben': ('#fefce8', '#713f12'),
    'Sonstiges':         ('#f3f4f6', '#374151'),
}


def category_badge_html(category: str) -> str:
    bg, color = CATEGORY_BADGE_COLORS.get(category, ('#f3f4f6', '#374151'))
    return (
        f'<span style="background:{bg};color:{color};font-size:0.72rem;'
        f'font-weight:600;padding:0.15rem 0.5rem;border-radius:4px;'
        f'white-space:nowrap;">{html.escape(category)}</span>'
    )


def calc_trend(current: float, previous: float):
    if previous == 0:
        return None
    return (current - previous) / previous * 100


# ============================================================
# SIDEBAR NAVIGARE
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="padding:0.5rem 0 1.5rem 0;">
        <div style="font-size:1.25rem;font-weight:700;color:white;margin-bottom:2px;">💶 Finanz Guru</div>
        <div style="font-size:0.8rem;color:#93c5fd;">Persönliche Finanzen · Lokal</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📤 Import", "💳 Transaktionen", "🎯 Budgets",
         "📈 Trends", "⚙️ Kategorieregeln", "📥 Export"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    df_all = get_transactions()
    if not df_all.empty:
        st.caption("**Schnellübersicht**")
        st.caption(f"📊 {len(df_all)} Transaktionen")
        if 'date' in df_all.columns:
            df_all['date'] = pd.to_datetime(df_all['date'])
            st.caption(f"📅 {df_all['date'].min().strftime('%b %Y')} → {df_all['date'].max().strftime('%b %Y')}")

    st.markdown("---")
    st.caption("🔒 Alle Daten lokal gespeichert in `data/finanzen.db`.")


def render_metric_card(label: str, value: str, card_class: str = "metric-card-income", trend=None, trend_label: str = ""):
    """Render tinted metric card with optional trend badge."""
    if trend is not None:
        arrow = "▲" if trend >= 0 else "▼"
        badge_class = "trend-up" if trend >= 0 else "trend-down"
        badge = f'<span class="trend-badge {badge_class}">{arrow} {abs(trend):.1f}% ggü. Vormonat</span>'
    elif trend_label:
        badge = f'<span class="trend-badge trend-info">{trend_label}</span>'
    else:
        badge = f'<span class="trend-badge trend-neu">–</span>'

    st.markdown(f"""
    <div class="metric-card {card_class}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{badge}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# DASHBOARD
# ============================================================
if page == "🏠 Dashboard":
    st.title("Dashboard")
    
    df = get_transactions()
    if df.empty:
        st.markdown("""
        <div class="panel" style="text-align: center; padding: 3rem;">
            <h2 style="margin-top: 0;">👋 Bun venit!</h2>
            <p style="color: #6b7280; font-size: 1.05rem;">
                Încarcă primul extras Deutsche Bank în secțiunea <b>📤 Import PDF</b> pentru a începe.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    
    # Filtru lună
    months_available = sorted(df['month'].unique(), reverse=True)
    
    col1, col2 = st.columns([2, 6])
    with col1:
        selected_month = st.selectbox(
            "Perioadă",
            options=['Toate'] + [str(m) for m in months_available],
            index=1 if len(months_available) > 0 else 0,
            label_visibility="collapsed"
        )
    
    if selected_month != 'Toate':
        df_filtered = df[df['month'].astype(str) == selected_month]
        period_label = selected_month
    else:
        df_filtered = df
        period_label = "Toată perioada"
    
    # Calcul metrici
    einnahmen = df_filtered[df_filtered['amount'] > 0]['amount'].sum()
    ausgaben = abs(df_filtered[df_filtered['amount'] < 0]['amount'].sum())
    saldo = einnahmen - ausgaben
    num_tx = len(df_filtered)
    savings_rate = (saldo / einnahmen * 100) if einnahmen > 0 else 0
    
    # Cards gradient
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Einnahmen", f"{einnahmen:,.2f} €",
                           card_class="metric-card-income", trend_label=period_label)
    with col2:
        render_metric_card("Ausgaben", f"{ausgaben:,.2f} €",
                           card_class="metric-card-expense", trend_label=period_label)
    with col3:
        balance_class = "metric-card-balance-pos" if saldo >= 0 else "metric-card-balance-neg"
        render_metric_card("Saldo", f"{saldo:+,.2f} €",
                           card_class=balance_class,
                           trend_label=f"Sparquote: {savings_rate:.1f}%" if einnahmen > 0 else "")
    with col4:
        render_metric_card("Transaktionen", f"{num_tx}",
                           card_class="metric-card-count", trend_label=period_label)
    
    st.write("")
    st.write("")
    
    # Grafice în coloane
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### Cheltuieli pe categorii")
        expenses = df_filtered[df_filtered['amount'] < 0].copy()
        if not expenses.empty:
            expenses['amount_abs'] = expenses['amount'].abs()
            cat_sum = expenses.groupby('category')['amount_abs'].sum().reset_index()
            cat_sum = cat_sum.sort_values('amount_abs', ascending=False)
            
            fig = px.pie(
                cat_sum, values='amount_abs', names='category',
                hole=0.55,
                color_discrete_sequence=[
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
                    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
                    '#14b8a6', '#eab308'
                ]
            )
            fig.update_traces(
                textposition='outside', 
                textinfo='label+percent',
                marker=dict(line=dict(color='white', width=2))
            )
            fig.update_layout(
                height=400, 
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(
                    text=f"<b>{ausgaben:,.0f}€</b><br><span style='font-size:12px;color:#6b7280'>Total</span>",
                    x=0.5, y=0.5, showarrow=False, font=dict(size=18, color='#111827')
                )]
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nu există cheltuieli în perioada selectată.")
    
    with col_right:
        st.markdown("### Top categorii")
        if not expenses.empty:
            top = cat_sum.head(8)
            fig = px.bar(
                top, x='amount_abs', y='category',
                orientation='h',
                color='amount_abs',
                color_continuous_scale=[[0, '#dbeafe'], [1, '#1e40af']],
                text='amount_abs'
            )
            fig.update_traces(
                texttemplate='%{text:,.0f} €',
                textposition='outside',
                textfont=dict(size=11)
            )
            fig.update_layout(
                height=400,
                yaxis={'categoryorder': 'total ascending', 'title': ''},
                xaxis={'title': '', 'showgrid': True, 'gridcolor': '#f3f4f6'},
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(t=20, b=20, l=20, r=60),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Evoluție sold cumulat
    st.markdown("### Evoluție sold")
    df_sorted = df_filtered.sort_values('date').copy()
    df_sorted['cumulative'] = df_sorted['amount'].cumsum()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['date'], y=df_sorted['cumulative'],
        mode='lines',
        line=dict(color='#3b82f6', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)',
        hovertemplate='<b>%{x|%d %b %Y}</b><br>Cumulat: %{y:,.2f} €<extra></extra>'
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#9ca3af", line_width=1)
    fig.update_layout(
        height=280,
        margin=dict(t=20, b=40, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(title='', showgrid=True, gridcolor='#f3f4f6', tickformat=',.0f'),
        xaxis=dict(title='', showgrid=False),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Ultimele tranzacții + Status buget side by side
    col_tx, col_budget = st.columns([3, 2])
    
    with col_tx:
        st.markdown("### Ultimele tranzacții")
        recent = df_filtered.head(8).copy()
        
        if not recent.empty:
            for _, tx in recent.iterrows():
                amount = tx['amount']
                color = "#10b981" if amount > 0 else "#ef4444"
                sign = "+" if amount > 0 else ""
                desc = tx.get('merchant') or tx['description']
                desc_display = desc[:55] + ('...' if len(desc) > 55 else '')
                
                st.markdown(f"""
                <div style="padding: 0.75rem 0; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <div style="font-weight: 500; color: #1f2937; font-size: 0.92rem;">{desc_display}</div>
                        <div style="color: #9ca3af; font-size: 0.78rem; margin-top: 2px;">
                            {tx['date'].strftime('%d %b %Y')} • {tx['category']}
                        </div>
                    </div>
                    <div style="color: {color}; font-weight: 600; font-size: 0.95rem;">
                        {sign}{amount:,.2f} €
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with col_budget:
        st.markdown("### Status buget")
        budgets = get_budgets()
        if budgets and selected_month != 'Toate' and not expenses.empty:
            any_shown = False
            for cat, limit in list(budgets.items())[:6]:
                if limit <= 0:
                    continue
                spent = expenses[expenses['category'] == cat]['amount_abs'].sum()
                pct = (spent / limit * 100) if limit > 0 else 0
                pct_display = min(pct, 100)
                
                if pct >= 100:
                    color = "#ef4444"
                    status_class = "status-over"
                    status_text = "Peste"
                elif pct >= 80:
                    color = "#f59e0b"
                    status_class = "status-warn"
                    status_text = "Aproape"
                else:
                    color = "#10b981"
                    status_class = "status-ok"
                    status_text = "OK"
                
                st.markdown(f"""
                <div style="margin-bottom: 0.85rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 500; color: #1f2937; font-size: 0.9rem;">{cat}</span>
                        <span class="status-pill {status_class}">{status_text}</span>
                    </div>
                    <div style="background: #f3f4f6; height: 6px; border-radius: 999px; overflow: hidden;">
                        <div style="background: {color}; height: 100%; width: {pct_display}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #6b7280; font-size: 0.78rem; margin-top: 3px;">
                        <span>{spent:,.0f} € din {limit:,.0f} €</span>
                        <span>{pct:.0f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                any_shown = True
            
            if not any_shown:
                st.caption("Setează bugete în secțiunea Bugete.")
        else:
            st.caption("Selectează o lună specifică și setează bugete pentru a vedea statusul.")


# ============================================================
# IMPORT PDF
# ============================================================
elif page == "📤 Import":
    st.title("Import extras Deutsche Bank")
    st.caption("Încarcă unul sau mai multe PDF-uri cu Kontoauszug. Tranzacțiile duplicate sunt ignorate automat.")
    
    uploaded_files = st.file_uploader(
        "Selectează PDF-uri",
        type=['pdf'],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.markdown(f"#### 📄 {uploaded_file.name}")
            
            temp_path = Path("uploads") / uploaded_file.name
            temp_path.parent.mkdir(exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                with st.spinner("Parsez PDF..."):
                    transactions = parse_db_pdf(str(temp_path))
                
                if not transactions:
                    st.warning("Nu am găsit tranzacții. Verifică dacă este un extras Deutsche Bank valid.")
                    continue
                
                df = pd.DataFrame(transactions)
                df = categorize_transactions(df)
                
                # Metrici rapide ale import-ului
                ein = df[df['amount'] > 0]['amount'].sum()
                aus = abs(df[df['amount'] < 0]['amount'].sum())
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Tranzacții", len(df))
                col2.metric("Einnahmen", f"{ein:,.2f} €")
                col3.metric("Ausgaben", f"{aus:,.2f} €")
                col4.metric("Perioadă", f"{df['date'].min()} → {df['date'].max()}")
                
                # Preview
                display_df = df[['date', 'merchant', 'category', 'amount']].copy()
                display_df.columns = ['Dată', 'Beneficiar', 'Categorie', 'Sumă (€)']
                st.dataframe(display_df, use_container_width=True, hide_index=True, height=350)
                
                col_save, col_cancel = st.columns([1, 4])
                with col_save:
                    if st.button(f"💾 Salvează în DB", key=f"save_{uploaded_file.name}", type="primary"):
                        n_inserted, n_duplicates = insert_transactions(df)
                        if n_inserted > 0:
                            st.success(f"✅ {n_inserted} tranzacții noi salvate.")
                        if n_duplicates > 0:
                            st.info(f"ℹ️ {n_duplicates} duplicate ignorate.")
                        
            except Exception as e:
                st.error(f"❌ Eroare la parsare: {e}")
                with st.expander("Detalii eroare"):
                    st.exception(e)
            
            st.markdown("---")


# ============================================================
# TRANZACȚII
# ============================================================
elif page == "💳 Transaktionen":
    st.title("Toate tranzacțiile")
    
    df = get_transactions()
    if df.empty:
        st.info("Nu există tranzacții. Încarcă un PDF mai întâi.")
        st.stop()
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Filtre într-o bară curată
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            date_from = st.date_input("De la", value=df['date'].min().date())
        with col2:
            date_to = st.date_input("Până la", value=df['date'].max().date())
        with col3:
            categories = ['Toate'] + sorted(df['category'].unique().tolist())
            selected_cat = st.selectbox("Categorie", categories)
        with col4:
            search = st.text_input("🔍 Căutare", placeholder="Merchant, descriere...")
    
    # Aplicare filtre
    mask = (df['date'].dt.date >= date_from) & (df['date'].dt.date <= date_to)
    if selected_cat != 'Toate':
        mask &= df['category'] == selected_cat
    if search:
        mask &= (df['description'].str.contains(search, case=False, na=False) | 
                 df['merchant'].fillna('').str.contains(search, case=False, na=False))
    
    df_filtered = df[mask].copy()
    
    # Rezumat filtru
    total = df_filtered['amount'].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Rezultate", len(df_filtered))
    col2.metric("Total pozitiv", f"{df_filtered[df_filtered['amount']>0]['amount'].sum():,.2f} €")
    col3.metric("Total negativ", f"{df_filtered[df_filtered['amount']<0]['amount'].sum():,.2f} €")
    
    # Editor
    st.markdown("##### Editează categoria direct în tabel")
    
    edit_df = df_filtered[['id', 'date', 'merchant', 'description', 'amount', 'category']].copy()
    
    edited = st.data_editor(
        edit_df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "date": st.column_config.DateColumn("Dată", disabled=True, format="DD.MM.YYYY", width="small"),
            "merchant": st.column_config.TextColumn("Beneficiar", disabled=True, width="medium"),
            "description": st.column_config.TextColumn("Descriere", disabled=True, width="large"),
            "amount": st.column_config.NumberColumn("Sumă (€)", format="%.2f", disabled=True, width="small"),
            "category": st.column_config.SelectboxColumn(
                "Categorie", 
                options=list(CATEGORIES.keys()) + ['Sonstiges'],
                width="medium"
            ),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        height=500
    )
    
    if st.button("💾 Salvează schimbări categorii", type="primary"):
        changes = 0
        for _, row in edited.iterrows():
            original = df_filtered[df_filtered['id'] == row['id']].iloc[0]
            if original['category'] != row['category']:
                update_category(row['id'], row['category'])
                changes += 1
        if changes > 0:
            st.success(f"✅ {changes} categorii actualizate.")
            st.rerun()
        else:
            st.info("Nu au fost modificări.")


# ============================================================
# BUGETE
# ============================================================
elif page == "🎯 Budgets":
    st.title("Bugete lunare")
    st.caption("Setează limite lunare pentru fiecare categorie. Vei primi alerte pe Dashboard când depășești.")
    
    budgets = get_budgets()
    df = get_transactions()
    
    avg_by_cat = pd.Series(dtype=float)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        current_month = df['month'].max()
        last_3m = df[df['month'] >= current_month - 2]
        expenses_3m = last_3m[last_3m['amount'] < 0].copy()
        expenses_3m['amount_abs'] = expenses_3m['amount'].abs()
        n_months = min(3, last_3m['month'].nunique() or 1)
        avg_by_cat = expenses_3m.groupby('category')['amount_abs'].sum() / n_months
    
    # Grid de bugete
    all_cats = list(CATEGORIES.keys()) + ['Sonstiges']
    
    # Filtrare: mai întâi categoriile care au cheltuieli reale
    cats_with_data = [c for c in all_cats if c in avg_by_cat.index and avg_by_cat[c] > 0]
    cats_without_data = [c for c in all_cats if c not in cats_with_data]
    
    tab1, tab2 = st.tabs([f"Categorii active ({len(cats_with_data)})", f"Alte categorii ({len(cats_without_data)})"])
    
    with tab1:
        for cat in cats_with_data:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{cat}**")
                suggest = avg_by_cat.get(cat, 0)
                if suggest > 0:
                    st.caption(f"Medie ultimele 3 luni: {suggest:,.2f} €")
            with col2:
                current = budgets.get(cat, 0.0)
                new_budget = st.number_input(
                    f"Buget {cat}",
                    min_value=0.0,
                    value=float(current),
                    step=10.0,
                    label_visibility="collapsed",
                    key=f"budget_active_{cat}"
                )
            with col3:
                if st.button(f"📋 Sugestie: {avg_by_cat.get(cat, 0):,.0f}€", key=f"suggest_{cat}"):
                    upsert_budget(cat, float(avg_by_cat.get(cat, 0)))
                    st.rerun()
            with col4:
                if st.button("💾", key=f"save_active_{cat}"):
                    upsert_budget(cat, new_budget)
                    st.toast(f"Salvat: {cat} = {new_budget:.2f} €", icon="✅")
                    st.rerun()
            st.markdown("<hr style='margin: 0.5rem 0; border-color: #f3f4f6;'/>", unsafe_allow_html=True)
    
    with tab2:
        for cat in cats_without_data:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{cat}**")
            with col2:
                current = budgets.get(cat, 0.0)
                new_budget = st.number_input(
                    f"Buget {cat}",
                    min_value=0.0,
                    value=float(current),
                    step=10.0,
                    label_visibility="collapsed",
                    key=f"budget_other_{cat}"
                )
            with col3:
                if st.button("💾", key=f"save_other_{cat}"):
                    upsert_budget(cat, new_budget)
                    st.rerun()


# ============================================================
# TRENDURI
# ============================================================
elif page == "📈 Trends":
    st.title("Analiză trenduri")
    
    df = get_transactions()
    if df.empty:
        st.info("Nu există date pentru analiză. Încarcă mai multe extrase pentru grafice mai relevante.")
        st.stop()
    
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    
    # Einnahmen vs Ausgaben
    st.markdown("### Venituri vs Cheltuieli pe luni")
    monthly = df.groupby('month').agg(
        einnahmen=('amount', lambda x: x[x > 0].sum()),
        ausgaben=('amount', lambda x: abs(x[x < 0].sum()))
    ).reset_index()
    monthly['saldo'] = monthly['einnahmen'] - monthly['ausgaben']
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly['month'], y=monthly['einnahmen'], 
        name='Venituri', 
        marker_color='#10b981',
        hovertemplate='<b>%{x}</b><br>Venituri: %{y:,.2f} €<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        x=monthly['month'], y=-monthly['ausgaben'], 
        name='Cheltuieli', 
        marker_color='#ef4444',
        hovertemplate='<b>%{x}</b><br>Cheltuieli: %{y:,.2f} €<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=monthly['month'], y=monthly['saldo'], 
        name='Saldo', mode='lines+markers',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10),
        hovertemplate='<b>%{x}</b><br>Saldo: %{y:,.2f} €<extra></extra>'
    ))
    fig.update_layout(
        barmode='relative', 
        height=420, 
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(title='€', showgrid=True, gridcolor='#f3f4f6'),
        xaxis=dict(title='', showgrid=False),
        legend=dict(orientation='h', y=1.1, x=0.5, xanchor='center')
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Evoluție pe categorii
    st.markdown("### Evoluție pe categorii")
    expenses = df[df['amount'] < 0].copy()
    expenses['amount_abs'] = expenses['amount'].abs()
    cat_monthly = expenses.groupby(['month', 'category'])['amount_abs'].sum().reset_index()
    
    all_cats_sorted = expenses.groupby('category')['amount_abs'].sum().sort_values(ascending=False).index.tolist()
    
    selected_cats = st.multiselect(
        "Alege categoriile",
        options=all_cats_sorted,
        default=all_cats_sorted[:5]
    )
    
    if selected_cats:
        cat_monthly_filtered = cat_monthly[cat_monthly['category'].isin(selected_cats)]
        fig = px.line(
            cat_monthly_filtered, x='month', y='amount_abs', 
            color='category', markers=True,
            color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
        )
        fig.update_traces(line=dict(width=2.5), marker=dict(size=8))
        fig.update_layout(
            height=420,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title='€', showgrid=True, gridcolor='#f3f4f6'),
            xaxis=dict(title='', showgrid=False),
            legend_title=''
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistici generale
    st.markdown("### Statistici generale")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cheltuială medie/lună", f"{monthly['ausgaben'].mean():,.2f} €")
    col2.metric("Venit mediu/lună", f"{monthly['einnahmen'].mean():,.2f} €")
    col3.metric("Saldo mediu/lună", f"{monthly['saldo'].mean():+,.2f} €")
    rate = (monthly['saldo'].sum() / monthly['einnahmen'].sum() * 100) if monthly['einnahmen'].sum() > 0 else 0
    col4.metric("Rată economisire", f"{rate:.1f} %")


# ============================================================
# REGULI
# ============================================================
elif page == "⚙️ Kategorieregeln":
    st.title("Reguli de categorizare")
    st.caption("Adaugă keyword-uri custom pentru categorizare automată. Se aplică la următorul import.")
    
    rules = get_rules()
    
    with st.form("add_rule", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            keyword = st.text_input("Keyword", placeholder="ex: edeka, netflix, tankstelle...")
        with col2:
            category = st.selectbox("Categorie", list(CATEGORIES.keys()) + ['Sonstiges'])
        with col3:
            st.write("")
            st.write("")
            submit = st.form_submit_button("➕ Adaugă", type="primary", use_container_width=True)
        
        if submit and keyword:
            update_rule(keyword.lower(), category)
            st.success(f"Regulă adăugată: `{keyword}` → {category}")
            st.rerun()
    
    st.markdown("### Reguli custom")
    if rules:
        rules_df = pd.DataFrame(rules.items(), columns=['Keyword', 'Categorie'])
        st.dataframe(rules_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nu ai reguli custom. Categorizarea folosește keyword-urile implicite de mai jos.")
    
    st.markdown("### Keyword-uri implicite")
    cols = st.columns(3)
    for idx, (cat, keywords) in enumerate(CATEGORIES.items()):
        with cols[idx % 3]:
            with st.expander(f"**{cat}** · {len(keywords)}"):
                st.caption(", ".join(keywords))


# ============================================================
# EXPORT
# ============================================================
elif page == "📥 Export":
    st.title("Export")
    
    df = get_transactions()
    if df.empty:
        st.info("Nu există date.")
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Export complet")
        st.caption("Toate tranzacțiile cu categorii și detalii.")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📄 Descarcă CSV",
            csv, "finanzen_export.csv", "text/csv",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        st.markdown("### Rezumat lunar")
        st.caption("Agregare pe lună și categorie.")
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M').astype(str)
        summary = df.groupby(['month', 'category']).agg(
            total=('amount', 'sum'),
            n_tx=('amount', 'count')
        ).reset_index()
        summary_csv = summary.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📊 Descarcă rezumat",
            summary_csv, "finanzen_summary.csv", "text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    st.markdown("### Previzualizare date")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)
