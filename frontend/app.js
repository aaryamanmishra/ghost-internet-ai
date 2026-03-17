document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('discoveryForm');
    const topicInput = document.getElementById('topicInput');
    const searchBtn = document.getElementById('searchBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsPanel = document.getElementById('resultsPanel');
    const analysisContent = document.getElementById('analysisContent');
    const sourcesList = document.getElementById('sourcesList');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const topic = topicInput.value.trim();
        if (!topic) return;

        // UI State: Loading
        searchBtn.classList.add('loading');
        searchBtn.disabled = true;
        resultsPanel.classList.add('hidden');
        statusMessage.classList.remove('hidden');

        try {
            const response = await fetch('/discover', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ topic })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to excavate data.');
            }

            const data = await response.json();
            
            // Render Results
            renderAnalysis(data.analysis);
            renderSources(data.sources);

            // UI State: Success
            statusMessage.classList.add('hidden');
            resultsPanel.classList.remove('hidden');

        } catch (error) {
            console.error('Error:', error);
            alert(`Archaeology Error: ${error.message}`);
            statusMessage.classList.add('hidden');
        } finally {
            // UI State: Reset Button
            searchBtn.classList.remove('loading');
            searchBtn.disabled = false;
        }
    });

    function renderAnalysis(rawText) {
        analysisContent.innerHTML = ''; // Clear previous

        // The text is structured using uppercase headings. We can regex match them to create nice cards.
        const sections = ['IDEA', 'ORIGINAL CONTEXT', 'WHY IT FAILED', 'MODERN REVIVAL', 'POTENTIAL IMPACT'];
        
        let parsedSections = {};
        
        // Split text dynamically based on the headers
        let currentSectionStr = rawText;
        
        sections.reverse().forEach(section => {
            const splitRegex = new RegExp(`\\b${section}\\b`);
            const parts = currentSectionStr.split(splitRegex);
            if (parts.length > 1) {
                parsedSections[section] = parts[1].trim();
                currentSectionStr = parts[0];
            } else {
                parsedSections[section] = "Data corrupted or unavailable in records.";
            }
        });
        
        sections.reverse(); // put back in correct order

        // Render each block with styled HTML
        sections.forEach(secName => {
            let content = parsedSections[secName] || '';
            // Clean up leading colons or dashes from the model response loosely
            content = content.replace(/^[:\-]/, '').trim();

            if (content) {
                const div = document.createElement('div');
                div.className = 'analysis-section';
                
                const label = document.createElement('div');
                label.className = 'section-label';
                label.innerText = secName;
                
                const body = document.createElement('div');
                body.className = 'section-content';
                body.innerText = content; // Using innerText for safe rendering

                div.appendChild(label);
                div.appendChild(body);
                analysisContent.appendChild(div);
            }
        });
        
        // Fallback if parsing failed due to unexpected model formats
        if (analysisContent.children.length === 0) {
            analysisContent.innerHTML = `<div class="analysis-section"><div class="section-content">${rawText.replace(/\\n/g, '<br>')}</div></div>`;
        }
    }

    function renderSources(sources) {
        sourcesList.innerHTML = '';
        sources.forEach((url, index) => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            
            try {
                // Shorten URL for display
                const domain = new URL(url).hostname.replace('www.', '');
                a.innerText = `[${index + 1}] ${domain}`;
            } catch (e) {
                a.innerText = `[${index + 1}] Source Link`;
            }
            
            li.appendChild(a);
            sourcesList.appendChild(li);
        });
    }
});
