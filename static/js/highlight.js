// word highlight script start

        const highlightWords = [
            'Blind',
            'Small Blind',
            'Big Blind',
            'Boss Blind',
            'Showdown Blind',
            'Ante',
            'Act',
            'Tag',
            'Edition',
            'Negative',
            'Mosaic',
            'Enhancement',
            'Steel',
            'Glass',
            'Gold',
            'Debuffed',
            'Seal',
            'Sticker',
            'Consumable',
            'Spectral Card',
            'Spectral',
            'Aura',
            'Ouija',
            'Tarot Card',
            'Tarot',
            'Wheel of Fortune',
            'The Devil',
            'Planet Card',
            'Planet',
            'Ceres',
            'Mercury',
            'Venus',
            'Earth',
            'Mars',
            'Jupiter',
            'Saturn',
            'Uranus',
            'Neptune',
            'Pluto',
            'Planet X',
            'Joker',
            'Jolly Joker',
            'Booster Pack',
            'Booster',
            'Hand',
            'Discard',
            'Scoring',
            'Scored',
            'Played',
            'Hand Size',
            'High Card',
            'Pair',
            '3 Of A Kind',
            'Three Of A Kind',
            '3OAK',
            '4 Of A Kind',
            'Four Of A Kind',
            '4OAK',
            '5 Of A Kind',
            'Five Of A Kind',
            '5OAK',
            'Straight',
            'Flush',
            'Straight Flush',
            'Royal Flush',
            'Flush Five',
            'Full House',
            'Flush House',
            'Playing Card',
            'Rank',
            'Suit',
            'Diamond',
            'Club',
            'Heart',
            'Spade',
            'Face Card'
        ];

const excludedClasses = ['tag', 'file', 'post-header'];

const regex = new RegExp(`\\b(${highlightWords.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})(?:s|'s)?\\b`, 'gi');

function walk(node) {
    // Skip excluded nodes
    if (node.nodeType === Node.ELEMENT_NODE) {
        const classList = Array.from(node.classList);
        if (classList.some(cls => excludedClasses.includes(cls))) return;

        for (let child of Array.from(node.childNodes)) {
            walk(child);
        }
    } else if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim().length > 0) {
        const parent = node.parentNode;
        const newHTML = node.nodeValue.replace(regex, match => `<span class="highlighted-word">${match}</span>`);
        if (newHTML !== node.nodeValue) {
            const span = document.createElement('span');
            span.innerHTML = newHTML;
            parent.replaceChild(span, node);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    walk(document.body);
});

// word highlight script end