from urlextract import URLExtract
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
from emoji import EMOJI_DATA
import string

def fetch_stats(selected_user,df):
    if selected_user!="Overall":
        df = df[df['user'] == selected_user]
    num_messages = df.shape[0]
    words = []
    for msg in df['message']:
        words.extend(msg.split())

    num_media=df[df['message']=="<Media omitted>"].shape[0]

    extractor = URLExtract()
    links = []
    for msg in df['message']:
        links.extend(extractor.find_urls(msg))
    return num_messages, len(words), num_media, len(links)

def fetch_most_busy_users(df):
    x = df['user'].value_counts().head()
    new_df=round((df['user'].value_counts()/df.shape[0])*100,2).reset_index().rename(columns={'user':'Name','count':'Percent'})
    return x , new_df

def create_wordcloud(selected_user,df):
    if selected_user!="Overall":
        df = df[df['user'] == selected_user]
    wc=WordCloud(width=500, height=500, min_font_size=10, background_color='white')
    temp = df[df['user'] != "group_notification"]
    temp = temp[temp['message'] != "<Media omitted>"]
    with open('stop_hinglish.txt', 'r') as f:
        stop_words = set(f.read().split())
    #nested function

    def remove_stop_words(message):
        y=[]
        for word in message.lower().split():
            if word not in stop_words:
                y.append(word)
        return " ".join(y)
    #creating image
    temp['message'] = temp['message'].apply(remove_stop_words)
    df_wc=wc.generate(temp['message'].str.cat(sep=" "))

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
    return return_df

def emoji_analysis(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    emojis = []
    for msg in df['message']:
        emojis.extend([c for c in msg if c in EMOJI_DATA])
    emoji_df=pd.DataFrame(Counter(emojis).most_common(len(Counter(emojis))))
    return emoji_df

def timeline(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    timeline_df=df.groupby(['year','month_num','month']).count()['message'].reset_index()
    time = []
    for i in range(timeline_df.shape[0]):
        time.append(timeline_df['month'][i] + "-" + str(timeline_df['year'][i]))
    timeline_df['time'] = time
    return timeline_df

def daily_timeline(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
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

def activity_heatmap(selected_user,df):
    if selected_user!="Overall":
        df=df[df['user']==selected_user]
    user_heatmap = df.pivot_table(index='day_name', columns='period', values='message', aggfunc='count').fillna(0)
    return user_heatmap

def load_bad_words():
    with open('bad_words.txt', 'r', encoding='utf-8') as f:
        return set(word.strip() for word in f if word.strip())

def toxic_analysis(selected_user, df):
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    df = df[df['user'] != 'group_notification']
    df = df[df['message'] != '<Media omitted>']

    bad_words = load_bad_words()

    toxic_words = []
    toxic_count_per_user = {}

    for _, row in df.iterrows():
        user = row['user']
        # remove punctuation
        message = row['message'].lower()
        message = message.translate(str.maketrans('', '', string.punctuation))
        words = message.split()

        count = 0
        for w in words:
            if w in bad_words:
                count += 1
                toxic_words.append(w)

        toxic_count_per_user[user] = toxic_count_per_user.get(user, 0) + count

    toxic_user_df = pd.DataFrame(
        toxic_count_per_user.items(),
        columns=['User', 'Toxic Word Count']
    ).sort_values(by='Toxic Word Count', ascending=False)

    toxic_words_df = pd.DataFrame(
        Counter(toxic_words).most_common(10),
        columns=['Word', 'Count']
    )

    return toxic_user_df, toxic_words_df

def reply_time_analysis(selected_user, df, gap_threshold_hours=6):

    # Filter user if not Overall
    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    # Remove group notifications
    df = df[df['user'] != 'group_notification'].copy()

    # Sort by date
    df = df.sort_values('date')

    # Shift previous values
    df['prev_user'] = df['user'].shift(1)
    df['prev_date'] = df['date'].shift(1)

    # Keep only rows where sender changed
    df = df[df['user'] != df['prev_user']]

    # Calculate reply time in minutes
    df['reply_time'] = (
        (df['date'] - df['prev_date']).dt.total_seconds() / 60
    )

    # Remove negative / NaN values
    df = df[df['reply_time'] > 0]

    # Exclude long gaps
    df = df[df['reply_time'] <= gap_threshold_hours * 60]

    # Calculate median reply time per user
    result = (
        df.groupby('user')['reply_time']
        .median()
        .reset_index()
        .sort_values('reply_time')
    )

    result.rename(columns={'reply_time': 'Median Reply Time (minutes)'}, inplace=True)

    return result

def fetch_ngrams(selected_user, df):

    if selected_user != "Overall":
        df = df[df['user'] == selected_user]

    # Remove system + media messages
    temp = df[df['user'] != "group_notification"]
    temp = temp[temp['message'] != "<Media omitted>"]

    # Load stopwords
    with open('stop_hinglish.txt', 'r') as f:
        stop_words = set(f.read().split())

    words = []

    for msg in temp['message']:
        clean_msg = msg.lower()
        clean_msg = clean_msg.translate(str.maketrans('', '', string.punctuation))

        for word in clean_msg.split():
            if word not in stop_words:
                words.append(word)

    # -------- BIGRAMS --------
    bigrams = []
    for i in range(len(words) - 1):
        bigrams.append(words[i] + " " + words[i+1])

    # -------- TRIGRAMS --------
    trigrams = []
    for i in range(len(words) - 2):
        trigrams.append(words[i] + " " + words[i+1] + " " + words[i+2])

    bigram_df = pd.DataFrame(Counter(bigrams).most_common(20),
                             columns=['Bigram', 'Count'])

    trigram_df = pd.DataFrame(Counter(trigrams).most_common(20),
                              columns=['Trigram', 'Count'])

    return bigram_df, trigram_df
