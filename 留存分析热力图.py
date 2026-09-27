from 数据预处理 import *
from 用户存留分析 import *
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib

# 设置中文字体（防止中文乱码，如果是Mac请换成'Arial Unicode MS'）
matplotlib.rc("font", family='SimHei')

def plot_retention_heatmap(retention_df):
    # 1. 准备绘图数据：将日期设为索引，只保留 Day1-Day7
    plot_data = retention_df.set_index('日期').iloc[:, 1:]

    # 2. 创建画布
    plt.figure(figsize=(12, 8))

    # 3. 绘制热力图
    # annot=True 显示数字，fmt=".1f" 保留一位小数，cmap 颜色方案
    sns.heatmap(plot_data, annot=True, fmt=".1f", cmap="YlGnBu",
                linewidths=.5, cbar_kws={'label': '留存率 (%)'})

    plt.title('用户行为留存率热力图 (11.25 - 12.03)', fontsize=15)
    plt.xlabel('留存天数', fontsize=12)
    plt.ylabel('基准日期', fontsize=12)

    # 旋转日期标签，防止重叠
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# 调用函数
if __name__ == '__main__':
    file_path = r"UserBehavior.csv"
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()
    cleaned_df, _ = process_data(file_path, start_date, end_date)
    retention_df = calculate_retention(cleaned_df)
    plot_retention_heatmap(retention_df)