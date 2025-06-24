import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title = "Income Expenditure Analysis")
st.header('Income Expenditure Analysis')
st.subheader('This is an analysis of my income expenditure')


### Load Dataframe from Excel File

excel_file = 'data/MasterFile.csv'
df = pd.read_csv(excel_file)

st.dataframe(df)


#Streamlit selection

year = df['Year'].unique().tolist()
month = df['Month'].unique().tolist()
df = df[df['Income/Expense'] == 'Expense']
category = df['Category'].unique().tolist()

## select Year
select_year = st.slider('Year:',min_value=min(year),max_value=max(year),value=(min(year),max(year)))

## multiselect

select_category = st.multiselect('Category',category)

mask = (df['Year'].between(*select_year)) & (df['Category'].isin(select_category))
result_no = df[mask].shape[0]
st.markdown(f'*Total Transaction: {result_no}*')

# --- GROUP DATAFRAME AFTER SELECTION
df_grouped = df[mask].groupby(by=['Year', 'Category']).count()[['MYR']].reset_index()



## Making a Pie Chart
#Filter the Income/Expense column to filter 'Expense'
df_expense = df[df['Income/Expense'] == 'Expense']

st.subheader('Expenses by Category')
pie_chart = px.pie(df_expense,
                   values='MYR',
                   names='Category')

st.plotly_chart(pie_chart)


#Line chart

total_spent = df.groupby('Month')['MYR'].sum().reset_index()
st.subheader('Amount Spent Each Month')
st.line_chart(total_spent.set_index('Month'))


