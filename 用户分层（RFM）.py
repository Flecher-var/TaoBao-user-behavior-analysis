from 数据预处理 import *
import pandas as pd

def RF_analysis(df):
    print("RF用户分层分析")
    buy_df = df[df['behavior_type'] == 'buy'].copy()
    analysis_date = buy_df['date'].max()
    rf_model = buy_df.groupby('user_id').agg({
        'date':lambda x: (analysis_date - x.max()).days,
        'item_id':'count'
    })
    rf_model.columns = ['R','F']
    rf_model['R_score'] = pd.qcut(
        rf_model['R'], q=4, labels=[4, 3, 2, 1],
        duplicates='drop')
    rf_model['F_score'] = pd.qcut(
        rf_model['F'].rank(method='first'), q=4,
        labels=[1, 2, 3, 4])

    r_avg = rf_model['R_score'].astype(int).mean()
    f_avg = rf_model['F_score'].astype(int).mean()

    def get_segment(row):
        r = int(row['R_score'])
        f = int(row['F_score'])

        if r > r_avg and f > f_avg:
            return '重要价值用户'
        if r < r_avg and f > f_avg:
            return '重要保持用户'
        if r > r_avg and f < f_avg:
            return '重要发展用户'
        else:
            return '一般保留用户'

    rf_model['用户分层'] = rf_model.apply(get_segment,axis=1)

    rf_summary = rf_model['用户分层'].value_counts().reset_index()
    rf_summary.columns = ['用户分层','人数']
    rf_summary['占比(%)'] = (rf_summary['人数']/rf_summary['人数'].sum() * 100).round(2)
    print(rf_summary)

    return rf_model,rf_summary

if __name__ == '__main__':
    file_path = 'UserBehavior.csv'
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()

    cleaned_df,missing_stats = process_data(file_path,start_date,end_date)
    rf_model, rf_summary = RF_analysis(cleaned_df)
