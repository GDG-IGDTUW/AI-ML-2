from urlextract import URLExtract
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
from emoji import EMOJI_DATA
import re

def fetch_stats(selected_user,df):
    if selected_user!="Overall":
        df = df[df['user'] == selected_user]
    num_messages = df.shape[0]
    words = []
    for msg in df['message'].dropna():
        words.extend(msg.split())

    num_media=df[df['message']=="<Media omitted>"].shape[0]

    extractor = URLExtract()
    links = []
    for msg in df['message']:
        links.extend(extractor.find_urls(msg))
    return num_messages, len(words), num_media, len(links)

def fetch_most_busy_users(df):
    x = df['user'].value_counts().head()
    new_df = round((df['user'].value_counts()/df.shape[0])*100,2).reset_index()
    new_df.columns = ['Name','Percent']

    return x , new_df

def create_wordcloud(selected_user, df):

    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    # Remove group notifications and media
    temp = df[df['user'] != 'group_notification']
    temp = temp[temp['message'] != '<Media omitted>']

    # Convert to string safely
    temp['message'] = temp['message'].astype(str)
    temp = temp[temp['message'].str.strip() != ""]

    #  No data protection
    if temp.empty:
        return None

    wc = WordCloud(
        width=500,
        height=500,
        min_font_size=10,
        background_color='white'
    )

    text = temp['message'].str.cat(sep=" ")
    df_wc = wc.generate(text)

    return df_wc


def most_common_words(selected_user, df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    temp = df[df['user'] != "group_notification"]
    temp = temp[temp['message'] != "<Media omitted>"]
    with open('stop_hinglish.txt', 'r') as f:
        stop_words = set(f.read().split())
    words = []
    for msg in temp['message']:
        for word in msg.lower().split():
            if word not in stop_words:
                words.append(word)

    return_df=pd.DataFrame(Counter(words).most_common(20))
    if return_df.empty:
        return None
    return return_df

def emoji_analysis(selected_user, df):
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]
    
    emojis = []
    for msg in df['message'].dropna():  # safety: ignore NaN messages
        emojis.extend([c for c in msg if c in EMOJI_DATA])
    
    if not emojis:  # no emojis found
        return pd.DataFrame(columns=['emoji', 'count'])
    
    emoji_df = pd.DataFrame(Counter(emojis).most_common(), columns=['emoji', 'count'])
    return emoji_df


def timeline(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
        if df.empty:  # 🚨 safety check
            return pd.DataFrame(columns=['year', 'month_num', 'month', 'message', 'time'])
    timeline_df=df.groupby(['year','month_num','month']).count()['message'].reset_index()
    time = []
    for i in range(timeline_df.shape[0]):
        time.append(timeline_df['month'][i] + "-" + str(timeline_df['year'][i]))
    timeline_df['time'] = time
    return timeline_df
    

def daily_timeline(selected_user, df):
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]
        if df.empty:  # check for empty filtered df
            return pd.DataFrame(columns=['date_only','message'])
    daily_timeline = df.groupby('date_only').count()['message'].reset_index()
    return daily_timeline


def week_activity_map(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    return df['day_name'].value_counts()

def month_activity_map(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    return df['month'].value_counts()

def activity_heatmap(selected_user, df):
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    # If no data after filtering
    if df.empty:
        return pd.DataFrame()

    user_heatmap = df.pivot_table(
        index='day_name',
        columns='period',
        values='message',
        aggfunc='count'
    ).fillna(0)

    # If pivot produced empty table
    if user_heatmap.shape[0] == 0 or user_heatmap.shape[1] == 0:
        return pd.DataFrame()

    return user_heatmap

def get_ngrams(selected_user, df, n):
    temp = df[df['user'] != 'group_notification']
    temp = temp[temp['message'] != '<Media omitted>\n']

    if selected_user != 'Overall':
        temp = temp[temp['user'] == selected_user]

    if temp.empty:  #  check if there are messages
        return []

    words = []
    for message in temp['message']:
        message = message.lower()
        message = re.sub(r'[^a-zA-Z\s]', '', message)
        words.extend(message.split())

    if len(words) < n:  # not enough words for n-grams
        return []

    ngrams = zip(*[words[i:] for i in range(n)])
    ngram_freq = Counter([" ".join(gram) for gram in ngrams])
    return ngram_freq.most_common(20)

