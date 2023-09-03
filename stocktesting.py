import pandas as pd
import pymysql
from datetime import timedelta
import matplotlib.pyplot as plt

conn = pymysql.connect(host='127.0.0.1', user='root', password='Quantum45**', db='INVESTAR', charset='utf8')
sql = "SELECT code, date, open, high, low, close, volume FROM daily_price"
df = pd.read_sql(sql, conn)

start_value = 1000000  # 시작 포트폴리오 가치
revenue = {}
success_rate = {}
code = '086520'
success_count = 0
k = 1000

current_df = df[(df['code'] == code) & (df['volume'] != 0)].copy()


# for k in range(10, 1000, 10):
current_df = current_df.tail(k)
current_df = current_df.dropna()


# 특정 주식에 대한 지표 계산
current_df['original'] = (((current_df['high'] - current_df['low'])/current_df['volume'])/current_df['close']).rolling(window=10).mean()
low = current_df['original'].rolling(window=20).min()
high = current_df['original'].rolling(window=20).max()
current_df['indicator'] = ((high - current_df['original']) / (high - low)) * 100
current_df['indicator'] = current_df['indicator'].rolling(window=10).mean()

portfolio = {'cash': 1000000, 'stock': 0}  # 1백만원 현금으로 시작

# 매수/매도 신호 초기화
current_df['signal'] = 0

# 매수 신호 설정
current_df.loc[current_df['indicator'] <= 10, 'signal'] = 1

# 매도 신호 설정
current_df.loc[current_df['indicator'] >= 90, 'signal'] = -1

for idx, row in current_df.iterrows():

    if row['signal'] == 1:  # 매수 신호
        # 전체 현금으로 매수하고, 수수료 0.15% 고려
        portfolio['stock'] += portfolio['cash'] / row['close'] * 0.99985
        portfolio['cash'] = 0

    elif row['signal'] == -1:  # 매도 신호
        # 전체 주식을 매도하고, 수수료 0.15% 고려
        portfolio['cash'] += portfolio['stock'] * row['close'] * 0.99785
        portfolio['stock'] = 0

    # 포트폴리오 총 가치 계산 (주식 가치 + 현금)
    current_df.loc[idx, 'portfolio_value'] = portfolio['stock'] * row['close'] + portfolio['cash']

final_value = portfolio['cash']
if portfolio['stock'] != 0:
    final_value += portfolio['stock'] * current_df['close'].iloc[-1]

profit_rate = ((final_value - start_value) / start_value) * 100

print(f"Code: {code}, K: {k}, Portfolio: {portfolio}, Final Value: {final_value:.2f}, Profit Rate: {profit_rate:.2f}%")

revenue[k] = profit_rate
if profit_rate > 0:
    success_count += 1
    success_rate[k] = (success_count / (k / 10)) * 100
else:
    success_rate[k] = 0

fig, ax1 = plt.subplots(figsize=(20,5))

# close 값 그리기
ax1.plot(current_df['date'], current_df['close'], 'g-')
ax1.set_xlabel('Date')
ax1.set_ylabel('Close', color='g')
ax1.tick_params(axis='y', labelcolor='g')

# indicator 값 그리기
ax2 = ax1.twinx()
ax2.plot(current_df['date'], current_df['indicator'], 'b-')
ax2.set_ylabel('Indicator', color='b')
ax2.tick_params(axis='y', labelcolor='b')

# Indicator 10과 90의 위치에 점선 그리기
ax2.axhline(y=10, color='black', linestyle='--')  # indicator 10 위치에 선 추가
ax2.axhline(y=90, color='black', linestyle='--')  # indicator 90 위치에 선 추가

red_marker = False
blue_marker = False

# `current_df`에 대한 반복문으로 변경
for i in range(len(current_df.index) - 1):
    if current_df['indicator'].iloc[i] > 10 and current_df['indicator'].iloc[i + 1] <= 10 and red_marker == False:
        ax1.plot(current_df['date'].iloc[i+1], current_df['close'].iloc[i + 1], 'r^')
        red_marker = True
        blue_marker = False
    if current_df['indicator'].iloc[i] < 90 and current_df['indicator'].iloc[i + 1] >= 90 and blue_marker == False:
        ax1.plot(current_df['date'].iloc[i+1], current_df['close'].iloc[i + 1], 'bv')
        blue_marker = True
        red_marker = False

fig.tight_layout()
plt.title(f"Close and Indicator for {code}")
plt.show()
