import matplotlib.pyplot as plt
import pandas as pd

def plot_event_trends(data):
    """
    生成事件趋势图
    :param data: 包含事件数据的 DataFrame
    """
    plt.figure(figsize=(10, 6))
    plt.plot(data['date'], data['event_count'], marker='o')
    plt.title('Event Trends Over Time')
    plt.xlabel('Date')
    plt.ylabel('Number of Events')
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    plt.show()

def plot_user_engagement(data):
    """
    生成用户参与度图
    :param data: 包含用户参与度数据的 DataFrame
    """
    plt.figure(figsize=(10, 6))
    plt.bar(data['user_id'], data['engagement_score'], color='skyblue')
    plt.title('User Engagement Scores')
    plt.xlabel('User ID')
    plt.ylabel('Engagement Score')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()