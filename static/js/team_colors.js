/**
 * Enhanced team color application script
 * This script ensures team colors are consistently applied throughout the site
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check if there's a selected team in the session
    const teamNameElement = document.querySelector('.selected-team');

    if (teamNameElement) {
        const teamName = teamNameElement.textContent.trim().toLowerCase();
        applyTeamColors(teamName);
    } else {
        console.log('No team selected, using default colors');
    }

    // Update goal song button behavior
    setupGoalSongButton();

    // Setup team selection functionality if on selection page
    setupTeamSelection();
});

/**
 * Apply team colors to the entire site
 * @param {string} teamName - The lowercase team name
 */
/**
 * Additional function to fix calendar backgrounds
 * Add this to your team_colors.js file
 */
function fixCalendarStyles(primaryColor, secondaryColor) {
    // Fix the calendar table if it exists
    const calendarTable = document.getElementById('calendarTable');
    if (calendarTable) {
        // Make the table background transparent to show the body background
        calendarTable.style.backgroundColor = 'transparent';
        calendarTable.style.borderColor = secondaryColor;

        // Fix table headers - should use secondary color
        const tableHeaders = calendarTable.querySelectorAll('th');
        tableHeaders.forEach(header => {
            header.style.backgroundColor = secondaryColor;
            header.style.color = getComputedStyle(document.body).getPropertyValue('--team-text-on-secondary').trim();
            header.style.borderColor = secondaryColor;
        });

        // Fix table cells - should be transparent
        const tableCells = calendarTable.querySelectorAll('td');
        tableCells.forEach(cell => {
            // Make cell background transparent
            cell.style.backgroundColor = 'transparent';

            // Set text color to match the readable color for the team's primary color
            cell.style.color = getComputedStyle(document.body).getPropertyValue('--team-text-on-primary').trim();

            // Keep match cards white
            const matchCards = cell.querySelectorAll('.match-card');
            matchCards.forEach(card => {
                card.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
                card.style.color = '#333';
            });
        });
    }
}

// Update the applyTeamColors function to include the calendar fix
function applyTeamColors(teamName) {
    if (!teamName) return;

    // First remove any existing team color classes
    document.body.classList.forEach(className => {
        if (className.startsWith('team-color-')) {
            document.body.classList.remove(className);
        }
    });

    // Add the specific team color class
    const teamClass = 'team-color-' + teamName.replace(/\s+/g, '-');
    document.body.classList.add(teamClass);

    // Also add the generic active class for general styling
    document.body.classList.add('team-color-active');

    console.log('Team colors applied:', teamClass);

    // Get computed color values
    const primaryColor = getComputedStyle(document.body).getPropertyValue('--team-primary').trim();
    const secondaryColor = getComputedStyle(document.body).getPropertyValue('--team-secondary').trim();

    // Directly set the background color of the body
    // This is a fallback in case CSS variables don't apply properly
    document.body.style.backgroundColor = primaryColor;

    // Ensure other elements are using the correct colors
    fixInlineStyles(primaryColor, secondaryColor);

    // Fix calendar specifically
    fixCalendarStyles(primaryColor, secondaryColor);
}

/**
 * Fix any elements with inline styles that might override our CSS variables
 */
function fixInlineStyles() {
    // Get computed team colors from CSS variables
    const primaryColor = getComputedStyle(document.body).getPropertyValue('--team-primary').trim();
    const secondaryColor = getComputedStyle(document.body).getPropertyValue('--team-secondary').trim();

    // Fix calendar table if it exists
    const calendarTable = document.getElementById('calendarTable');
    if (calendarTable) {
        // Remove any inline background color
        calendarTable.style.backgroundColor = '';

        // Fix table headers
        const tableHeaders = calendarTable.querySelectorAll('th');
        tableHeaders.forEach(header => {
            if (header.style.backgroundColor) {
                header.style.backgroundColor = '';
            }
        });
    }

    // Fix any buttons with inline background styles
    const buttons = document.querySelectorAll('.btn, .btn-month');
    buttons.forEach(button => {
        if (button.style.backgroundImage || button.style.backgroundColor) {
            button.style.backgroundImage = 'none';
            button.style.backgroundColor = '';
        }
    });

    // Fix any elements with inline border colors
    const borderedElements = document.querySelectorAll('.match-card, table, th, td');
    borderedElements.forEach(element => {
        if (element.style.borderColor) {
            element.style.borderColor = '';
        }
    });
}

/**
 * Setup the goal song button functionality
 */
function setupGoalSongButton() {
    const goalSongButton = document.getElementById('goal-song-button');
    const goalAudio = document.getElementById('goal-song-audio');

    if (goalSongButton && goalAudio) {
        let isPlaying = false;

        goalSongButton.addEventListener('click', function() {
            if (!isPlaying) {
                goalAudio.play();
                goalSongButton.classList.add('playing');
                document.getElementById('goal-icon').textContent = '🔊';
                isPlaying = true;
            } else {
                goalAudio.pause();
                goalAudio.currentTime = 0;
                goalSongButton.classList.remove('playing');
                document.getElementById('goal-icon').textContent = '🔈';
                isPlaying = false;
            }
        });

        goalAudio.addEventListener('ended', function() {
            goalSongButton.classList.remove('playing');
            document.getElementById('goal-icon').textContent = '🔈';
            isPlaying = false;
        });
    }
}

/**
 * Setup team selection functionality
 */
function setupTeamSelection() {
    // Only run on pages with team selection
    const teamItems = document.querySelectorAll('.team-selection-item');
    if (teamItems.length === 0) return;

    // First, see if we have a pre-selected team from the input
    const hiddenInput = document.getElementById('selected-team-input');
    if (hiddenInput && hiddenInput.value) {
        const selectedItem = document.getElementById('team-' + hiddenInput.value);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
    }

    teamItems.forEach(item => {
        item.addEventListener('click', function() {
            // Get team ID from the element ID
            const teamId = this.id.replace('team-', '');

            // Remove active class from all teams
            teamItems.forEach(otherItem => {
                otherItem.classList.remove('active');
            });

            // Add active class to selected team
            this.classList.add('active');

            // Update hidden input value
            const teamInput = document.getElementById('selected-team-input');
            if (teamInput) {
                teamInput.value = teamId;
            }

            // Get team name and apply preview colors
            const teamName = this.querySelector('.team-name').textContent.trim().toLowerCase();
            if (teamName) {
                applyTeamColors(teamName);
            }
        });
    });
}