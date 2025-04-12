import streamlit as st
import pandas as pd
import pymysql
from sqlalchemy import create_engine
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from PIL import Image
import plotly.express as px
import openai
import pytesseract
from PIL import Image
from rapidfuzz import process, fuzz
import json
from datetime import date
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --- DB Connection ---
def get_connection():
    return pymysql.connect(
        host="127.0.0.1",
        port = 3306,
        user="root",
        password="123_Bootcamp",
        database="final_project"
    )

# SQLAlchemy engine for Pandas `.to_sql()`
engine = get_connection()
sqlalchemy_engine = create_engine("mysql+pymysql://root:123_Bootcamp@127.0.0.1:3306/final_project")



#Title and presentation

st.title(" Welcome to Carbon Foodprint ♻️")
st.subheader("What is it ?")
st.markdown("Carbon Foodprint helps users track their carbon footprint by visualizing CO₂ emissions of their food and grocery prices. " \
"It offers insights into product categories, sustainability tips, and progress tracking to support more eco-friendly choices.")



# Load and display the image in the sidebar
logo = Image.open("D:\Documents\GitHub\Final_Project\Foodprint.png")
st.sidebar.image(logo, use_container_width =True)

#User data with chat GPT
openai.api_key = "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"


# --- KPI Dashboard ---

def load_all_data(view_type):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Time grouping logic
    date_parse_expr = """
    STR_TO_DATE(`Date`, 
        CASE
            WHEN `Date` LIKE '%/%/%' THEN '%Y/%m/%d'
            WHEN `Date` LIKE '%-%-%' THEN '%Y-%m-%d'
            ELSE NULL
        END
    )
    """

    if view_type == 'Week':
        period_expr = f"CONCAT(YEAR({date_parse_expr}), '-W', LPAD(WEEK({date_parse_expr}, 1), 2, '0'))"
    elif view_type == 'Month':
        period_expr = f"DATE_FORMAT({date_parse_expr}, '%Y-%m')"
    else:
        period_expr = f"YEAR({date_parse_expr})"

    period_col = f"{period_expr} AS period"
    group_by = period_expr

    # Emissions query
    emissions_query = f"""
    SELECT {period_col}, ROUND(SUM(total_kg_co2), 2) AS total_co2_kg
    FROM master_data
    GROUP BY {group_by}
    ORDER BY period;
    """

    # Price query
    price_query = f"""
    SELECT {period_col}, ROUND(SUM(price), 2) AS price
    FROM master_data
    GROUP BY {group_by}
    ORDER BY period;
    """

    # Pollution price query
    pollution_query = f"""
    SELECT 
        {period_col},
        ROUND(SUM(price), 2) AS price,
        ROUND(SUM(total_kg_co2), 2) AS total_co2_kg,
        ROUND(SUM(price) / NULLIF(SUM(total_kg_co2), 0), 2) AS pollution_price
    FROM master_data
    GROUP BY {group_by}
    ORDER BY period;
    """

    # Product breakdown query
    product_query = f"""
    SELECT 
        {period_col},
        product_family AS category,
        title AS product,
        ROUND(SUM(total_kg_co2), 2) AS total_co2_kg
    FROM master_data
    GROUP BY {group_by}, product_family, title
    ORDER BY period, total_co2_kg DESC;
    """

    # Supply chain percentage query
    supplychain_query = f"""
    SELECT 
        period,
        CONCAT(ROUND((farming / total_co2_kg) * 100, 2), '%') AS farming_percentage,
        CONCAT(ROUND((processing / total_co2_kg) * 100, 2), '%') AS processing_percentage,
        CONCAT(ROUND((packaging / total_co2_kg) * 100, 2), '%') AS packaging_percentage,
        CONCAT(ROUND((transport / total_co2_kg) * 100, 2), '%') AS transport_percentage,
        CONCAT(ROUND((retail / total_co2_kg) * 100, 2), '%') AS retail_percentage,
        CONCAT(ROUND((consumption / total_co2_kg) * 100, 2), '%') AS consumption_percentage
    FROM (
        SELECT 
            {period_expr} AS period,
            ROUND(SUM(total_kg_co2), 2) AS total_co2_kg,
            SUM(total_kg_co2_farming) AS farming,
            SUM(total_kg_co2_processing) AS processing,
            SUM(total_kg_co2_packaging) AS packaging,
            SUM(total_kg_co2_transport) AS transport,
            SUM(total_kg_co2_retail) AS retail,
            SUM(total_kg_co2_consumption) AS consumption
        FROM master_data
        GROUP BY {group_by}
    ) AS sub
    ORDER BY period;
    """

    # Execute all queries
    cursor.execute(emissions_query)
    emissions_df = pd.DataFrame(cursor.fetchall())

    cursor.execute(price_query)
    price_df = pd.DataFrame(cursor.fetchall())

    cursor.execute(pollution_query)
    pollution_df = pd.DataFrame(cursor.fetchall())

    cursor.execute(product_query)
    product_df = pd.DataFrame(cursor.fetchall())

    cursor.execute(supplychain_query)
    supply_chain_df = pd.DataFrame(cursor.fetchall())

    cursor.close()
    conn.close()

    return emissions_df, price_df, pollution_df, product_df, supply_chain_df






# Upload User Data Section

st.title("🍽️ What did you buy today ?")

with st.expander("Choose an option"):
    
    page = st.radio("🛒 Update Your Groceries", ["Upload Receipt", "Manual Search"])
    selected_columns = [ 
         "title", "slug", "product_family", "origin", "price",
        "total_kg_co2", "total_kg_co2_farming", "total_kg_co2_processing",
        "total_kg_co2_packaging", "total_kg_co2_transport",
        "total_kg_co2_retail", "total_kg_co2_consumption"
    ]
    receipt_date = st.date_input("🗓️ Select Date", value=date.today())

    # --- Load Product Table (Shared) ---
    product_input_df = pd.read_sql("SELECT * FROM product", con=engine)

    # --- Upload Receipt Page ---
    if page == "Upload Receipt":
        st.title("📸 Upload a Scanned Receipt")

        receipt_image = st.file_uploader("Upload a scanned receipt image (JPG/PNG)", type=["jpg", "jpeg", "png"])

        if receipt_image is not None:
            image = Image.open(receipt_image)
            receipt_text = pytesseract.image_to_string(image)

            prompt = f"""
            This is a scanned receipt. Extract only the list of products under the "Description" section.
            If there are values on the QTE x P U column, repeat the line above in "Description".
            Ignore prices, totals, and other metadata. Return the product names in a JSON format like:

            {{
            "products": ["Product 1", "Product 2", "..."]
            }}

            Receipt text:
            \"\"\"
            {receipt_text}
            \"\"\"
            """

            with st.spinner("Extracting product list from receipt..."):
                
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result_text = response['choices'][0]['message']['content']
                product_data = json.loads(result_text)
                products = product_data.get("products", [])

                df_receipt = pd.DataFrame(products, columns=["title"])
                df_receipt["Date"] = receipt_date

                st.success("✅ Products extracted:")
                st.dataframe(df_receipt)

                # Save receipt_data
                df_receipt.to_sql("receipt_data", con=sqlalchemy_engine, if_exists="append", index=False)

                # Fuzzy match with product table
                st.info("🔍 Matching with 'product' table...")

                matched_data = []
                for title in df_receipt["title"]:
                    match, score, idx = process.extractOne(title, product_input_df["title"], scorer=fuzz.partial_ratio)
                    if score > 60:
                        product_row = product_input_df.iloc[idx][selected_columns].copy()
                        product_row["Date"] = receipt_date
                        matched_data.append(product_row.to_dict())  # 👈 Convert Series to dict

                if matched_data:
                    df_master = pd.DataFrame(matched_data)
                    df_master.to_sql("master_data", con=sqlalchemy_engine, if_exists="append", index=False)
                    st.success("✅ Matched products added to 'master_data'")
                    st.dataframe(df_master)
                else:
                    st.warning("⚠️ No high-confidence matches found.")


    # --- Manual Search Page ---
    elif page == "Manual Search":
        st.title("🔍 Manually Add Groceries")

        # Filter by Category
        categories = sorted(product_input_df["product_family"].dropna().unique())
        selected_category = st.selectbox("📂 Filter by Category", options=["All"] + categories)

        if selected_category != "All":
            filtered_products = product_input_df[product_input_df["product_family"] == selected_category]
        else:
            filtered_products = product_input_df

        selected_titles = st.multiselect(
            "🔎 Search and select products to add:",
            options=filtered_products["title"].tolist(),
        )

        if "manual_cart" not in st.session_state:
            st.session_state.manual_cart = []

        if st.button("🛒 Add Selected to Cart"):
            new_items = filtered_products[filtered_products["title"].isin(selected_titles)].copy()
            new_items["Date"] = receipt_date
            st.session_state.manual_cart.extend(new_items.to_dict(orient="records"))
            st.success(f"✅ {len(new_items)} product(s) added to cart")
            
        if st.session_state.manual_cart:
            st.subheader("🛍️ Manual Cart")
            df_cart = pd.DataFrame(st.session_state.manual_cart)
            st.dataframe(df_cart)


            if st.button("✅ Submit Cart to Master Data"):

                conn = engine
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                

                placeholders = ', '.join(['%s'] * len(selected_titles))

                query = f"""
                SELECT {', '.join(selected_columns)}
                FROM product
                WHERE title IN ({placeholders});
                """

                cursor.execute(query, selected_titles) 
                product_data = cursor.fetchall()
                search_df = pd.DataFrame(product_data, columns=selected_columns)

                # Merge with manually selected cart
                df_cart = pd.DataFrame(st.session_state.manual_cart)
                df_final = df_cart.merge(search_df, on="title", how="left")

                # Save final result to master_data table
                columns_present = [col for col in selected_columns if col in df_final.columns]
                df_final_cleaned = df_final[columns_present]
                #df_final_cleaned["Date"] = receipt_date
                df_final_cleaned.to_sql("master_data", con=sqlalchemy_engine, if_exists="append", index=False)

                st.success("🎉 Cart submitted to your profile")
                st.session_state.manual_cart = []


# --- Main Dashboard ---

st.title("📊 Grocery KPIs Dashboard")
st.sidebar.title("Dashboard Options")
# Select Time View (Week, Month, Year)
view_option = st.sidebar.selectbox("Select Time View", ["Week", "Month", "Year"])

emissions_df, price_df, pollution_df, product_df, supply_chain_df = load_all_data(view_option)
product_df["period"] = product_df["period"].astype(str).str.replace('.0', '', regex=False)
all_periods = sorted(
    [p for p in product_df["period"].unique() if pd.notna(p)],  # Filter out NaN and None
    reverse=True
)
selected_period = st.sidebar.selectbox(
    "Filter by period:",
    ["Select a period"] + all_periods
)

filtered_products = product_df[product_df["period"] == selected_period]
category_impact = filtered_products.groupby("category")["total_co2_kg"].sum().reset_index()
category_impact = category_impact.sort_values(by="total_co2_kg", ascending=False)
selected_emissions = emissions_df[emissions_df['period'] == selected_period]
total_co2_emission = selected_emissions['total_co2_kg'].sum()

#Supply chain

percent_df = supply_chain_df.copy()
for col in percent_df.columns[1:]:
    percent_df[col] = percent_df[col].str.replace('%', '').astype(float)



with st.expander("Selected period data"):
    st.write("Want to learn more about your latest purchase ? It's here !")

    # ♻️ Dynamic Sustainability Tip
    st.subheader("🌱 Sustainability Tip for this period")
    st.write(f"For the {selected_period}, you produced **{total_co2_emission:.2f} kg of CO₂**")


    if not category_impact.empty:
        top_category = category_impact.iloc[0]["category"]
        top_emission = category_impact.iloc[0]["total_co2_kg"]

        advice_map = {
            "Viandes et Poissons": "Try replacing red meat with plant-based proteins like lentils, beans, or tofu. They're much lower in CO₂ and often cheaper too!",
            "Crèmerie et Produits laitiers": "Consider plant-based alternatives like oat milk or almond milk, which have a lower carbon footprint.",
            "Epicerie sucrée": "Reduce processed snack consumption and opt for fresh, local fruit or nuts.",
            "Boissons": "Cut down on bottled drinks and sugary beverages — filtered tap water is the most eco-friendly drink!",
            "Epicerie salée": "Cook at home when possible and choose locally produced food to reduce emissions from transportation and packaging.",
        }

        advice_text = advice_map.get(top_category, f"Consider reducing your consumption of products in the '{top_category}' category or choosing more sustainable alternatives.")

        st.markdown(f"""
        ### 🌍 Highest Emission Category: **{top_category}**
        In this period alone, it contributed **{top_emission:,.2f} kg of CO₂**.

        **Advice:** {advice_text}
        """)
    else:
        st.info("No data available for this period to generate a sustainability tip.")

    # 📉 Emissions Trend Compared to Previous Period (Fixed Logic)
    st.subheader("📈 Emissions Trend Compared to Previous Period")

    # Sort periods in ascending order so earlier periods come first
    #all_periods = sorted(product_df["period"].unique())

    # Make sure selected period is not the first one
    if selected_period in all_periods:
        current_index = all_periods.index(selected_period)
        
        if current_index > 0:
            previous_period = all_periods[current_index + 1]
            current_data = product_df[product_df["period"] == selected_period]
            previous_data = product_df[product_df["period"] == previous_period]

            current_total = current_data["total_co2_kg"].sum()
            previous_total = previous_data["total_co2_kg"].sum()

            delta = current_total - previous_total
            percent_change = (delta / previous_total) * 100 if previous_total != 0 else 0

            if delta < 0:
                st.success(f"✅ Great job! CO₂ emissions decreased by {abs(percent_change):.2f}% compared to {previous_period}. Keep it up! 🌿")
            elif delta > 0:
                st.warning(f"⚠️ Emissions increased by {percent_change:.2f}% compared to {previous_period}. Maybe review your choices in high-emission categories.")
            else:
                st.info(f"ℹ️ Emissions stayed the same compared to {previous_period}. Try to make small change to decrease your impact!")
        else:
            st.info("Not enough previous data to compare.")
    else:
        st.info("Selected period not found in data.")




    # 📊 Dynamic Horizontal Bar Chart of CO₂ by Category for Selected Period
    st.subheader("📊 CO₂ Emissions by Category (for selected period)")

    # Sort by highest emissions
    category_impact_sorted = category_impact.sort_values(by="total_co2_kg", ascending=False)

    # Show horizontal bar chart with labels
    fig = px.bar(
        category_impact_sorted,
        x="total_co2_kg",
        y="category",
        orientation="h",
        title=f"CO₂ Emissions by Category — {selected_period}",
        color="category",
        text="total_co2_kg",
        color_discrete_sequence=px.colors.sequential.RdBu
    )

    # Improve layout
    fig.update_traces(texttemplate='%{text:.2f} kg', textposition='outside')
    fig.update_layout(
        yaxis_title="",
        xaxis_title="Total CO₂ (kg)",
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    st.plotly_chart(fig, use_container_width=True)

    # 🛒 Supply Chain CO₂ Breakdown (as % of total footprint for selected period)
    st.subheader("🛒 Supply Chain CO₂ Breakdown (as % of total footprint for selected period)")

    # Filter and melt the data for pie chart
    selected_data = percent_df[percent_df['period'] == selected_period]
    melted = selected_data.drop(columns="period").melt(var_name="stage", value_name="percentage")

    # Create pie chart
    fig = px.pie(
        melted,
        names="stage",
        values="percentage",
        title=f"Supply Chain Footprint Breakdown – {selected_period}",
        color_discrete_sequence=px.colors.sequential.YlOrRd,
        hole=0.5
    )

    st.plotly_chart(fig, use_container_width=True)

    # Product Breakdown
    st.subheader("📦 Product Footprint by Category")

    st.dataframe(filtered_products)

with st.expander("Trend view"):
    st.write("Want to see how you are doing in the long term?")
    # CO2 Trend
    st.subheader("🌍 Total CO₂ Emissions Trend")
    st.line_chart(emissions_df.set_index('period')['total_co2_kg'])


    st.subheader("🛒Evolution of Supply Chain CO₂ Breakdown (as % of total footprint)")
    melted_df = percent_df.melt(id_vars='period', var_name='Stage', value_name='Percentage')
    
    fig = px.bar(
        melted_df,
        x='period',
        y='Percentage',
        color='Stage',
        title=f'Supply Chain CO₂ % Breakdown by {view_option}',
        labels={'period': view_option, 'Percentage': '% of Total CO₂'},
    )

    fig.update_layout(
        barmode='stack',
        xaxis_tickangle=-45,
        height=500,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)


    # Price Trend
    st.subheader("💸 Total Grocery Price Trend")
    st.line_chart(price_df.set_index('period')['price'])

    # Pollution Price Table
    st.subheader("🧮 Pollution Price (€/kg CO₂)")
    st.line_chart(pollution_df.set_index('period')['pollution_price'])