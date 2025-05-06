document.addEventListener("DOMContentLoaded", function () {
    function updatePlayerDropdown() {
        let teamField = document.querySelector("#id_team");
        let positionField = document.querySelector("#id_position");
        let playerField = document.querySelector("#id_player");

        if (!teamField || !positionField || !playerField) {
            console.log("DEBUG: Fields not found!");
            return;
        }

        function fetchPlayers() {
            let teamId = teamField.value;
            let position = positionField.value;

            if (teamId && position) {
                console.log(`Fetching players for Team: ${teamId}, Position: ${position}`);

                fetch(`/admin/matches/player/?team_id=${teamId}&position=${position}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log("Players received:", data);
                        playerField.innerHTML = ""; // Clear old options

                        if (data.length === 0) {
                            let option = document.createElement("option");
                            option.textContent = "No players available";
                            option.disabled = true;
                            playerField.appendChild(option);
                        } else {
                            data.forEach(player => {
                                let option = document.createElement("option");
                                option.value = player.id;
                                option.textContent = `${player.first_name} ${player.last_name}`;
                                playerField.appendChild(option);
                            });
                        }
                    })
                    .catch(error => console.error("Error fetching players:", error));
            }
        }

        teamField.addEventListener("change", fetchPlayers);
        positionField.addEventListener("change", fetchPlayers);
    }

    updatePlayerDropdown();
});
