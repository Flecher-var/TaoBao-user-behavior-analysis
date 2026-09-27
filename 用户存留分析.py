"""
留存分析：计算日 / 周 / 月留存率，分析不同用户群体的留存差异，
挖掘高留存用户行为特征；
"""
import pandas as pd
from 数据预处理 import *
def calculate_retention(df):
    print("用户存留率分析")
    user_active_days = df[['user_id','date']].drop_duplicates()
    retention_table = []
    unique_dates = sorted(user_active_days['date'].unique())
    for i, base_date in enumerate(unique_dates):
        base_users = set(user_active_days[user_active_days['date'] == base_date]['user_id'])
        base_count = len(base_users)
        retention_row = {'日期':base_date,'初始人数':base_count}
        for day_offset in range(1,8):
            target_idx = i + day_offset
            if target_idx < len(unique_dates):
                target_date = unique_dates[target_idx]
                target_users = set(user_active_days[user_active_days['date'] == target_date]['user_id'])
                retained_users = len(base_users & target_users)
                retention_row[f'Day{day_offset}'] = round(retained_users / base_count * 100, 2)
            else:
                retention_row[f'Day{day_offset}'] = None
        retention_table.append(retention_row)
    retention_df = pd.DataFrame(retention_table)
    print(retention_df)
    return retention_df

if __name__ == '__main__':
    file_path = 'UserBehavior.csv'
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()
    cleaned_df, _ = process_data(file_path, start_date, end_date)
    calculate_retention(cleaned_df)