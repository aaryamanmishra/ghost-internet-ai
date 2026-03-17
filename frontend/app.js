document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('discoveryForm');
    const topicInput = document.getElementById('topicInput');
    const searchBtn = document.getElementById('searchBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsPanel = document.getElementById('resultsPanel');
    // We no longer need analysisContent as we target the specific ID's created
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
            
            // Render Results passing the entire data object now instead of just the string
            renderAnalysis(data);
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

    function renderAnalysis(data) {
        // Backend now returns both:
        // - Preferred: data.analysis (Future Lab contract)
        // - Back-compat: flat keys (older contract)
        const analysis = (data && data.analysis && typeof data.analysis === 'object') ? data.analysis : (data || {});

        // Idea
        document.getElementById('aiIdeaDescription').innerText = analysis.idea || data.idea || "Data missing.";

        // Metrics
        const prob = (data && data.revival_probability !== undefined) ? data.revival_probability : (analysis.revival_probability !== undefined ? analysis.revival_probability : undefined);
        const feas = (analysis.feasibility_score !== undefined) ? analysis.feasibility_score : data.feasibility_score;
        const impact = (analysis.impact_score !== undefined) ? analysis.impact_score : data.impact_score;
        const breakthrough = analysis.key_breakthrough_needed || data.key_breakthrough_needed || "Unknown";

        document.getElementById('metricProbability').innerText = prob !== undefined ? `${prob}%` : "--%";
        document.getElementById('metricFeasibility').innerText = feas !== undefined ? `${feas}/10` : "--/10";
        document.getElementById('metricImpact').innerText = impact !== undefined ? `${impact}/10` : "--/10";
        document.getElementById('breakthroughNeed').innerText = breakthrough;

        // Expert Panel
        document.getElementById('historianAnalysis').innerText = analysis.historian_analysis || data.historian_analysis || "No historical records found.";
        document.getElementById('engineerAnalysis').innerText = analysis.engineer_analysis || data.engineer_analysis || "No engineering logs found.";
        document.getElementById('futuristAnalysis').innerText = analysis.futurist_analysis || data.futurist_analysis || "No future projections available.";
        document.getElementById('consensusSummary').innerText = analysis.consensus_summary || data.consensus_summary || "Consensus could not be reached.";

        // Innovation Tree
        const treeList = document.getElementById('innovationTree');
        treeList.innerHTML = '';
        if (data.innovation_tree && Array.isArray(data.innovation_tree)) {
            data.innovation_tree.forEach(item => {
                const li = document.createElement('li');
                li.innerText = item;
                treeList.appendChild(li);
            });
        }

        // Future Timeline
        const timelineList = document.getElementById('futureTimeline');
        timelineList.innerHTML = '';
        if (data.timeline && Array.isArray(data.timeline)) {
            data.timeline.forEach(item => {
                const li = document.createElement('li');
                li.innerText = item;
                timelineList.appendChild(li);
            });
        }
    }

    function renderSources(sources) {
        sourcesList.innerHTML = '';
        if (!sources || !Array.isArray(sources) || sources.length === 0) {
            const li = document.createElement('li');
            li.innerText = 'No sources available (scraping may have failed).';
            sourcesList.appendChild(li);
            return;
        }

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
