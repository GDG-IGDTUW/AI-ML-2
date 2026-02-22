import streamlit as st
import preprocessor, helper
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

st.sidebar.title("Whatsapp Chat Analyser")

uploaded_files = st.sidebar.file_uploader(
    "Choose 1–3 WhatsApp chat files",
    accept_multiple_files=True
)

if uploaded_files:

    chat_dataframes = {}

    for file in uploaded_files:
        data = file.read().decode("utf-8")
        df = preprocessor.preprocessor(data)
        chat_dataframes[file.name] = df

    # ==========================================================
    # 🔥 MULTI CHAT MODE (2–3 FILES) → SIDE-BY-SIDE COMPARISON
    # ==========================================================

    if len(uploaded_files) > 1:

        if st.sidebar.button("Compare Chats"):

            st.title("Side-by-Side Chat Comparison")

            cols = st.columns(len(chat_dataframes))

            for col, (chat_name, df) in zip(cols, chat_dataframes.items()):

                with col:
                    st.subheader(chat_name)

                    num_messages, words, media, links = helper.fetch_stats("Overall", df)

                    st.write("Messages:", num_messages)
                    st.write("Words:", words)
                    st.write("Media:", media)
                    st.write("Links:", links)

    # ==========================================================
    # 🔥 SINGLE CHAT MODE → FULL DETAILED ANALYSIS
    # ==========================================================

    elif len(uploaded_files) == 1:

        df = list(chat_dataframes.values())[0]

        # fetch unique users
        user_list = df['user'].unique().tolist()
        try:
            user_list.remove('group_notification')
        except ValueError:
            pass

        user_list.sort()
        user_list.insert(0, "Overall")

        selected_user = st.sidebar.selectbox("Show analysis wrt", user_list)

        if st.sidebar.button("Show Detailed Analysis"):

            # ---------------- TOP STATS ----------------
            st.title("Top Statistics")

            num_messages, words, num_media, num_links = helper.fetch_stats(selected_user, df)

            col1, col2, col3, col4 = st.columns(4)

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

            # ---------------- MONTHLY TIMELINE ----------------
            st.title("Monthly Timeline")
            timeline_df = helper.timeline(selected_user, df)
            fig, ax = plt.subplots()
            ax.plot(timeline_df['time'], timeline_df['message'], color="purple")
            plt.xticks(rotation=45)
            st.pyplot(fig)

            # ---------------- DAILY TIMELINE ----------------
            st.title("Daily Timeline")
            daily_timeline = helper.daily_timeline(selected_user, df)
            fig, ax = plt.subplots()
            ax.plot(daily_timeline['date_only'], daily_timeline['message'])
            plt.xticks(rotation=45)
            st.pyplot(fig)

            # ---------------- ACTIVITY MAP ----------------
            st.title("Activity Map")

            col1, col2 = st.columns(2)

            with col1:
                st.header("Most Busy Day")
                busy_day = helper.week_activity_map(selected_user, df)
                fig, ax = plt.subplots()
                ax.bar(busy_day.index, busy_day.values)
                plt.xticks(rotation=45)
                st.pyplot(fig)

            with col2:
                st.header("Most Busy Month")
                busy_month = helper.month_activity_map(selected_user, df)
                fig, ax = plt.subplots()
                ax.bar(busy_month.index, busy_month.values, color='orange')
                plt.xticks(rotation=45)
                st.pyplot(fig)

            # ---------------- HEATMAP ----------------
            st.title("Activity HeatMap")
            user_heatmap = helper.activity_heatmap(selected_user, df)

            if user_heatmap.empty:
                st.warning("Not enough data to generate heatmap for this selection.")
            else:
                fig, ax = plt.subplots()
                sns.heatmap(user_heatmap, ax=ax)
                st.pyplot(fig)

            # ---------------- BUSIEST USERS ----------------
            if selected_user == "Overall":
                st.title("Most Busy Users")
                x, new_df = helper.fetch_most_busy_users(df)
                col1, col2 = st.columns(2)

                with col1:
                    fig, ax = plt.subplots()
                    ax.bar(x.index, x.values)
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                with col2:
                    st.dataframe(new_df)

            # ---------------- WORD CLOUD ----------------
            st.title("Word Cloud")
            df_wc = helper.create_wordcloud(selected_user, df)
            fig, ax = plt.subplots()
            ax.imshow(df_wc)
            ax.axis("off")
            st.pyplot(fig)

            # ---------------- MOST COMMON WORDS ----------------
            # ---------------- MOST COMMON WORDS ----------------
            st.title("Most Common Words")
            most_common_df = helper.most_common_words(selected_user, df)

            if most_common_df.empty:
                st.warning("Not enough data to display most common words.")
            else:
                fig, ax = plt.subplots()
                ax.barh(
                    most_common_df.iloc[:, 0],
                    most_common_df.iloc[:, 1]
                )
                ax.invert_yaxis()
                st.pyplot(fig)

            # ---------------- EMOJI ANALYSIS ----------------
            mpl.rcParams['font.family'] = 'Segoe UI Emoji'

            st.title("Emoji Analysis")
            emoji_df = helper.emoji_analysis(selected_user, df)

            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(emoji_df)

            with col2:
                if not emoji_df.empty:
                    fig, ax = plt.subplots()
                    top_emoji = emoji_df.head(10)
                    ax.pie(top_emoji[1], labels=top_emoji[0], autopct="%0.2f")
                    st.pyplot(fig)