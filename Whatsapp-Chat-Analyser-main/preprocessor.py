import re
import pandas as pd

def preprocessor(data):
     # Normalize weird unicode spaces
    data = data.replace('\u202f', ' ').replace('\u00a0', ' ')
    # Pattern handles dates like 12/2/23 or 12-02-2023, with optional AM/PM
    pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s+(\d{1,2}:\d{2}(?:\s?[APMapm]{2})?)\s*-\s'

    # Extract dates and times
    dates = re.findall(pattern, data)
    timestamps = ['{}, {}'.format(date, time) for date, time in dates]

    print("SAMPLE TIMESTAMPS:", timestamps[:10])

    # Split messages
    messages = re.split(pattern, data)[1:]
    messages = [m for m in messages if m.strip() != '']

    # Align lengths
    min_len = min(len(messages), len(timestamps))
    messages = messages[:min_len]
    timestamps = timestamps[:min_len]

    # Create dataframe
    df = pd.DataFrame({
        'user_message': messages,
        'message_date': timestamps
    })

    # Split user and message
    users, texts = [], []
    for msg in df['user_message']:
        entry = re.split(r'([\w\W]+?):\s', msg, maxsplit=1)
        if len(entry) > 1:
            users.append(entry[0])
            texts.append(entry[1])
        else:
            users.append('group_notification')
            texts.append(entry[0])
    df['user'] = users
    df['message'] = texts

    # Try parsing 12-hour format (MM/DD/YY)
    df['message_date'] = pd.to_datetime(
    timestamps,
    format='%m/%d/%y, %I:%M %p',
    errors='coerce'
)

    # Fill missing values using 24-hour format
    df['message_date'] = df['message_date'].combine_first(
    pd.Series(
        pd.to_datetime(timestamps, format='%m/%d/%y, %H:%M', errors='coerce'),
        index=df.index
    )
)


    df.dropna(subset=['message_date'], inplace=True)

    # Extract features
    df['year'] = df['message_date'].dt.year
    df['month'] = df['message_date'].dt.month_name()
    df['month_num'] = df['message_date'].dt.month
    df['day_name'] = df['message_date'].dt.day_name()
    df['hour'] = df['message_date'].dt.hour
    df['date_only'] = df['message_date'].dt.date

    # Hour periods
    df['period'] = df['hour'].apply(lambda h: f"{h}-{(h+1)%24:02d}")

    return df
