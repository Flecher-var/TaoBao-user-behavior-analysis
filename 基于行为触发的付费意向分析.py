"""
- 付费分析：分析付费用户的行为偏好、消费金额分布，识别高价值付费用户的核心特征。
"""
"""
这里由于数据集中不直接包含商品单价或订单金额，用行为偏好分析 作为提升
转为分析购买与其他行为的关系
    路径偏好：用户是“直接买”多，还是“收藏/加购后再买”多？
    品类偏好：哪些类目（category_id）的购买转化率最高？
    时段偏好：高价值用户（买得次数多的人）通常在哪个时间点下单？
"""
from 数据预处理 import *

def analyze_buy_preferences(df):
    print("付费行为偏好深度分析")

    #提取所有产生过购买行为的用户ID
    pay_user_ids = df[df['behavior_type'] == 'buy']['user_id'].unique()
    pay_user_df = df[df['user_id'].isin(pay_user_ids)]

    #计算这些付费用户在【购买前】各种行为的分布
    behavior_counts = pay_user_df['behavior_type'].value_counts()
    print("付费用户全路径行为分布：")
    print(behavior_counts)
    pv_count = behavior_counts.get('pv',0)
    buy_count = behavior_counts.get('buy',0)
    conversion_ratio = pv_count / buy_count if buy_count != 0 else 0
    print(f"全站行为转化比 (PV/Buy): {conversion_ratio:.2f}")
    print(f"注：平均每 {conversion_ratio:.1f} 次点击产生 1 次购买")

    #品类偏好：哪些类目的购买量最高
    top_buy_categories = df[df['behavior_type'] == 'buy']['category_id'].value_counts().head(10)
    print(top_buy_categories)

    #复购率分析
    buy_counts_per_user = df[df['behavior_type'] == 'buy'].groupby('user_id').size()
    repurchase_rate = (buy_counts_per_user > 1).sum() / len(buy_counts_per_user)
    print(f"\n用户复购率 (Repurchase Rate): {repurchase_rate:.2%}")

    return top_buy_categories

if __name__ == '__main__':
    file_path = r"UserBehavior.csv"
    start_date = pd.to_datetime('2017-11-25').date()
    end_date = pd.to_datetime('2017-12-03').date()
    cleaned_df, _ = process_data(file_path, start_date, end_date)
    analyze_buy_preferences(cleaned_df)

'''
1. 转化漏斗：从“海量浏览”到“精准决策”
数据洞察：全站转化比为 32.94。这意味着用户平均点击 33 次才会产生 1 次购买。
2. 品类矩阵：识别“流量池”与“利润池”
数据洞察：类目 1464116、2735466、2885642 是购买量最高的前三大品类。
3. 用户粘性：复购率折射出的品牌护城河
数据洞察：复购率高达 65.81%。
'''