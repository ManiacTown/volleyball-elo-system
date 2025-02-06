#
#
# UI FOR elo_project

import streamlit as st
import pandas as pd
from elo_project import create_match, create_match_button, get_all_players, get_player_stats, get_all_names  # Import necessary functions

# Set up Streamlit UI
st.title("Volleyball ELO System")

# **Step 1: Enter Player Names BEFORE Clicking the Button**
#players_input = st.text_area("Enter player names (comma-separated):")

all_players = get_all_names()
players_input = st.multiselect("Select players for the match:", all_players)

def main():

    if st.button("Create Teams"):

        if players_input:  # Ensure input is not empty
            player_list = [name.strip() for name in players_input]#.split(",")]

            if player_list:
                team1, team2 = create_match_button(player_list) # Modify based on function input

                # Display the teams
                st.subheader("Generated Teams")
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Team 1**")
                    st.write(f"{team1}")  # Debugging Step 4

                with col2:
                    st.write("**Team 2**")
                    st.write(f"{team2}")  # Debugging Step 4
        else:
            st.write("⚠️ Please enter player names before clicking the button!")

    if "team1" in st.session_state and "team2" in st.session_state:
            if st.button("Process Match"):
                st.write("Which team won?")
                col1, col2 = st.columns(2)
                team1_won = col1.button(f"{', '.join(st.session_state.team1)}")
                team2_won = col2.button(f"{', '.join(st.session_state.team2)}")
                
                score = st.text_input("Enter match score (21-XX format):")
                if score:
                    try:
                        score1, score2 = map(int, score.split('-'))
                        if score1 != 21 and score2 != 21:
                            st.error("One team must have 21 points.")
                        else:
                            winner = st.session_state.team1 if team1_won else st.session_state.team2
                            loser = st.session_state.team2 if team1_won else st.session_state.team1
                            st.success(f"Winner: {', '.join(winner)} | Loser: {', '.join(loser)} | Score: {score}")
                    except ValueError:
                        st.error("Invalid score format. Use 21-XX.")
                    
    # Button to view leaderboard
    if st.button("View Leaderboard"):
        player_stats = get_player_stats()
        df = pd.DataFrame(player_stats).T  # Convert dictionary to DataFrame
        df = df.sort_values(by="elo", ascending=False)  # Sort by ELO
        st.write(df)

    if st.button("Click to get free ELO!"):
        st.write("Gullible")

    # Placeholder for match log feature (to be implemented)
    st.write("Match log feature coming soon!")


if __name__ == "__main__":
    main()
