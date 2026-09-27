from 数据预处理 import *
import pandas as pd

def analyze_data(df):
    print("正在进行漏斗分析")
    behavior_count = df['behavior_type'].value_counts()
    return behavior_count
def perform_funnel_analysis(df):
    print("进行行为漏斗分析")
    behavior_count = df['behavior_type'].value_counts().reindex(['pv', 'fav', 'cart', 'buy'])
    funnel  = pd.DataFrame(behavior_count).reset_index()
    funnel.columns = ['环节','行为总量']
    #计算单一路径转化率
    funnel['总转换率(%)'] = (funnel['行为总量'] / funnel['行为总量'].iloc[0] * 100).round(2)
    #计算环节之间的转化率(当前步骤 / 上一步骤)
    funnel['环节转化率(%)'] = (funnel['行为总量'] / funnel['行为总量'].shift(1) * 100).round(2)
    funnel.fillna({'环节转化率(%)': 100.0},inplace=True)
    print(funnel)

    #关键业务打印
    pv_to_buy= funnel.loc[funnel['环节'] == 'buy','总转换率(%)'].values[0]
    print(f"\n[业务结论] 最终付费转化率 (PV -> Buy): {pv_to_buy}%")

    return funnel

if __name__ == '__main__':
    file_path = 'UserBehavior.csv'
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()
    cleaned_df, _ = process_data(file_path, start_date, end_date)
    print(analyze_data(cleaned_df))
    perform_funnel_analysis(cleaned_df)