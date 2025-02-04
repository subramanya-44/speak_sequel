import seaborn as sns
import matplotlib.pyplot as plt

def plot_bar_chart(df, x_col, y_col):
    plt.figure(figsize=(10, 5))
    sns.barplot(x=x_col, y=y_col, data=df)
    plt.xticks(rotation=45)
    plt.title(f"{x_col} vs {y_col}")
    plt.show()

# Example Usage
df = execute_sql_query("SELECT product, SUM(sales) FROM dataset GROUP BY product ORDER BY SUM(sales) DESC LIMIT 5;")
plot_bar_chart(df, "product", "SUM(sales)")
