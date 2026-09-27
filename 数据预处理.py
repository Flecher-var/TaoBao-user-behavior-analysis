import pandas as pd
import matplotlib.pyplot as plt

def process_data(file_path,start_date,end_date):
    dtypes = {'user_id':'int32','item_id':'int32','category_id':'int32','behavior_type': 'object','timestamp':'int64'}
    columns = ['user_id','item_id','category_id','behavior_type','timestamp']
    total_missing = pd.Series(0,index=columns + ['datetime','date','hour'])
    process_chunks=[]
    csv_chunks = pd.read_csv(
        file_path,header=None,names=columns,dtype = dtypes,chunksize=500000
    )
    for chunk in csv_chunks:
        chunk['datetime'] = pd.to_datetime(chunk['timestamp'], unit='s')
        chunk['date'] = chunk['datetime'].dt.date
        chunk['hour'] = chunk['datetime'].dt.hour
        chunk_filtered = chunk[(chunk['date'] >= start_date) & (chunk['date'] <= end_date)]
        chunk_filtered = chunk_filtered.drop_duplicates(subset=columns, keep='first')
        process_chunks.append(chunk_filtered)
        total_missing += chunk_filtered.isnull().sum()
    df_processed = pd.concat(process_chunks,ignore_index=True)
    return df_processed,total_missing

def audit_data(df):
    '''
    检查数据质量的函数
    '''
    #1、检查日期范围
    dates = df['date'].unique()
    print(f'包含的日期：{sorted(dates)}')

    #2、检查用户异常行为
    top_users = df.groupby('user_id').size().sort_values(ascending=False).head(10)
    print(f"\n活跃度前10的用户（检查爬虫）:\n{top_users}")

    #3、检查小时分布
    hourly_dist = df['hour'].value_counts().sort_index()
    print("\n小时分布数据已准备，正在生成图表...")
    #绘图：24小时流量分布图
    plt.figure(figsize = (10,6))
    hourly_dist.plot(kind='bar',color='skyblue',edgecolor='black')
    plt.xlabel("Hour of Day")
    plt.ylabel("Behavior Count")
    plt.grid(axis='y', linestyle='--',alpha=0.7)
    plt.show()

if __name__ == '__main__':
    file_path = 'UserBehavior.csv'
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()
    cleaned_df,missing_stats = process_data(file_path,start_date,end_date)
    #缺失值
    print(missing_stats)
    #数据量确认
    print(len(missing_stats))
    # 行为分布查看
    print(cleaned_df['behavior_type'].value_counts())


    #统计每个小时的行为总数
    hourly_counts = cleaned_df['hour'].value_counts().sort_values(ascending=False)
    #计算每个小时占总体流量的百分比
    hourly_pct = hourly_counts / hourly_counts.sum()
    ## 计算累计百分比 (Cumulative Sum)
    hourly_cumsum = hourly_pct.cumsum()

    # 筛选出覆盖了前 85% 行为的主流小时段
    core_hours = hourly_cumsum[hourly_cumsum <= 0.85]

    print("--- 贡献了 85% 流量的核心小时段 ---")
    print(core_hours)

    top_hours_list = sorted(core_hours.index.tolist())
    print(f"\n结论：85% 以上的用户活跃行为集中在每天的以下时段：")
    print(f"{top_hours_list[0]} 点 到 {top_hours_list[-1]} 点")

    # 质量校验
    audit_data(cleaned_df)