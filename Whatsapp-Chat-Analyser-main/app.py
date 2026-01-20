import streamlit as st
import preprocessor,helper
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

st.sidebar.title("Whatsapp Chat Analyser")
uploaded_file = st.sidebar.file_uploader("Choose a file")
if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    data=bytes_data.decode("utf-8")
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
        fig,ax=plt.subplots()
        ax.plot(timeline_df['time'], timeline_df['message'], color="purple")
        plt.xticks(rotation=45)
        st.pyplot(fig)

        #daily Timeline
        st.title("Daily Timeline")
        daily_timeline=helper.daily_timeline(selected_user,df)
        fig, ax = plt.subplots()
        ax.plot(daily_timeline['date_only'], daily_timeline['message'])
        plt.xticks(rotation=45)
        st.pyplot(fig)

        #activity map
        st.title("Activity Map")
        col1,col2=st.columns(2)
        with col1:
            st.header("Most Busy Day")
            busy_day=helper.week_activity_map(selected_user,df)
            fig,ax=plt.subplots()
            ax.bar(busy_day.index,busy_day.values)
            plt.xticks(rotation=45)
            st.pyplot(fig)
        with col2:
            st.header("Most Busy Month")
            busy_month = helper.month_activity_map(selected_user, df)
            fig, ax = plt.subplots()
            ax.bar(busy_month.index, busy_month.values,color='orange')
            plt.xticks(rotation=45)
            st.pyplot(fig)

        # weekly activity heatmap
        st.title("Activity HeatMap")
        user_heatmap=helper.activity_heatmap(selected_user,df)
        fig,ax=plt.subplots()
        ax=sns.heatmap(user_heatmap)
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
        df_wc=helper.create_wordcloud(selected_user,df)
        fig, ax=plt.subplots()
        ax.imshow(df_wc)
        st.pyplot(fig)

        # most common words
        most_common_df=helper.most_common_words(selected_user,df)
        fig, ax= plt.subplots()
        ax.barh(most_common_df[0],most_common_df[1])
        plt.xticks(rotation='vertical')
        st.title("Most common words")
        st.pyplot(fig)

        #analysing emojis
        mpl.rcParams['font.family'] = 'Segoe UI Emoji'
        emoji_df=helper.emoji_analysis(selected_user,df)
        st.title("Emoji Analysis")
        col1 , col2= st.columns(2)
        with col1:
            st.dataframe(emoji_df)
        with col2:
            fig, ax=plt.subplots()
            top_emoji=emoji_df.head(10)
            ax.pie(top_emoji[1], labels=top_emoji[0], autopct="%0.2f")
            st.pyplot(fig)

        # Toxic / Profanity Analysis
        st.title("Toxic words / Profanity Analysis")
        toxic_user_df, toxic_words_df = helper.toxic_analysis(selected_user, df)

        st.caption(
        "⚠️ Disclaimer: This analysis is keyword-based using a small custom list. "
         "It does not understand context and may produce false positives."
        )

        st.subheader("Toxic Word Count per User")
        st.dataframe(toxic_user_df)

        st.subheader("Most Common Flagged Words")
        st.dataframe(toxic_words_df)


