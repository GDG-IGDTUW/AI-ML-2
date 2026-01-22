import streamlit as st
import preprocessor,helper
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import helper
import pandas as pd

st.sidebar.title("Whatsapp Chat Analyser")
uploaded_file = st.sidebar.file_uploader("Choose a file")
if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    try:
        data = bytes_data.decode("utf-8")
    except UnicodeDecodeError:
        data = bytes_data.decode("utf-16")

    df=preprocessor.preprocessor(data)

    # fetch unique users
    user_list = df['user'].unique().tolist()
    try:
         user_list.remove('group_notification')
    except ValueError:
        pass
    user_list.sort()
    user_list.insert(0,"Overall")
    selected_user=st.sidebar.selectbox("Show analysis wrt", user_list)

    if st.sidebar.button("Show Analysis"):
        st.title("Top Statistics")
        num_messages, words , num_media , num_links=helper.fetch_stats(selected_user,df)
        col1, col2, col3, col4=st.columns(4)
        with col1:
            st.header("Total Messages")
            st.title(num_messages)
        with col2:
            st.header("Total Words")
            st.title(words)
        with col3:
            st.header("Media Shared")
            st.title(num_media)
        with col4:
            st.header("Links Shared")
            st.title(num_links)

        #Monthly timeline
        st.title("Monthly Timeline")
        timeline_df=helper.timeline(selected_user,df)
        if not timeline_df.empty:
            fig,ax=plt.subplots()
            ax.plot(timeline_df['time'], timeline_df['message'], color="purple")
            plt.xticks(rotation=45)
            st.pyplot(fig)
        else:
            st.warning("⚠️ Not enough data for timeline.")

        #daily Timeline
        st.title("Daily Timeline")
        daily_timeline=helper.daily_timeline(selected_user,df)
        if not daily_timeline.empty:
            fig, ax = plt.subplots()
            ax.plot(daily_timeline['date_only'], daily_timeline['message'])
            plt.xticks(rotation=45)
            st.pyplot(fig)
        else:
            st.warning("⚠️ Not enough data for timeline.")


        #activity map
        st.title("Activity Map")
        col1,col2=st.columns(2)
        with col1:
            st.header("Most Busy Day")
            busy_day=helper.week_activity_map(selected_user,df)
            if not busy_day.empty:
                fig,ax=plt.subplots()
                ax.bar(busy_day.index,busy_day.values)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.warning("⚠️ Not enough data for timeline.")
        with col2:
            st.header("Most Busy Month")
            busy_month = helper.month_activity_map(selected_user, df)
            if not busy_month.empty:
                fig, ax = plt.subplots()
                ax.bar(busy_month.index, busy_month.values,color='orange')
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.warning("⚠️ Not enough data for timeline.")

        # weekly activity heatmap
        st.title("Activity HeatMap")
        user_heatmap = helper.activity_heatmap(selected_user, df)
        if user_heatmap.empty:
            st.warning("⚠️ Not enough data available to generate heatmap for this selection.")
        else:
            user_heatmap = user_heatmap.fillna(0)   # safety
            fig, ax = plt.subplots()
            sns.heatmap(user_heatmap, ax=ax)
            st.pyplot(fig)


        #finding the busiest users in the the group
        if selected_user=="Overall":
            st.title("Most Busy Users")
            x, new_df=helper.fetch_most_busy_users(df)
            fig, ax=plt.subplots()

            col1 , col2 =st.columns(2)
            with col1:
                ax.bar(x.index, x.values)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            with col2:
                st.dataframe(new_df)

        #wordcloud
        st.title("Word Cloud")
        df_wc = helper.create_wordcloud(selected_user, df)

        if df_wc is None:
            st.warning("⚠️ Not enough data to generate wordcloud.")
        else:
            fig, ax = plt.subplots()
            ax.imshow(df_wc)
            ax.axis("off")
            st.pyplot(fig)


        # most common words
        most_common_df=helper.most_common_words(selected_user,df)

        # Rename columns to ensure they exist
        if most_common_df is not None and not most_common_df.empty:
            if most_common_df.shape[1] == 2:
                most_common_df.columns = ['word', 'count']
                fig, ax = plt.subplots()
                ax.barh(most_common_df['word'], most_common_df['count'])
                plt.xticks(rotation='vertical')
                st.title("Most common words")
                st.pyplot(fig)
        else:
                st.warning("⚠️ Not enough data to show most common words.")

        

        #analysing emojis
        mpl.rcParams['font.family'] = 'Segoe UI Emoji'
        emoji_df=helper.emoji_analysis(selected_user,df)
        st.title("Emoji Analysis")
        if emoji_df.empty:
            st.warning("⚠️ Not enough emoji data to display.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(emoji_df)
                with col2:
                    fig, ax = plt.subplots()
                    top_emoji = emoji_df.head(10)
                    if top_emoji is None or top_emoji.empty:
                        st.warning("No emojis found for this user.")
                    else:
                        ax.pie(top_emoji['count'], labels=top_emoji['emoji'], autopct="%0.2f")


                    st.pyplot(fig)



        #flowcharts
        st.title("📊 Bigram Analysis (Top 20)")
        bigrams = helper.get_ngrams(selected_user, df, 2)
        if bigrams:
            bigram_df = pd.DataFrame(bigrams, columns=['Bigram', 'Count'])
            st.bar_chart(bigram_df.set_index("Bigram"))


        st.title("📊 Trigram Analysis (Top 20)")
        trigrams = helper.get_ngrams(selected_user, df, 3)
        if trigrams:
            trigram_df = pd.DataFrame(trigrams, columns=['Trigram', 'Count'])
            st.bar_chart(trigram_df.set_index("Trigram"))


