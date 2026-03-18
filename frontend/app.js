document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('discoveryForm');
    const topicInput = document.getElementById('topicInput');
    const searchBtn = document.getElementById('searchBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsPanel = document.getElementById('resultsPanel');
    // We no longer need analysisContent as we target the specific ID's created
    const sourcesList = document.getElementById('sourcesList');
    const saveBtn = document.getElementById('saveBtn');

    // Modal elements
    const modal = document.getElementById('ideaModal');
    const closeModal = document.getElementById('closeModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    function showModal(title, htmlContent) {
        modalTitle.innerText = title;
        modalBody.innerHTML = htmlContent;
        modal.classList.remove('hidden');
    }

    closeModal.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });

    let lastDiscovery = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const topic = topicInput.value.trim();
        if (!topic) return;

        // UI State: Loading
        searchBtn.classList.add('loading');
        searchBtn.disabled = true;
        resultsPanel.classList.add('hidden');
        statusMessage.classList.remove('hidden');
        saveBtn.disabled = true;

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
            lastDiscovery = { topic, data };
            
            // Render Results passing the entire data object now instead of just the string
            renderAnalysis(data);
            renderSources(data.sources);
            renderTechnology(data);
            renderResearchPapers(data.research_papers);
            renderPatents(data.related_patents);
            renderCompanies(data.related_companies);
            renderIssues(data.issues);
            await refreshSavedIdeas();

            // UI State: Success
            statusMessage.classList.add('hidden');
            resultsPanel.classList.remove('hidden');
            saveBtn.disabled = false;

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

    saveBtn.addEventListener('click', async () => {
        if (!lastDiscovery) return;
        const { topic, data } = lastDiscovery;
        const analysis = (data && data.analysis && typeof data.analysis === 'object') ? data.analysis : (data || {});

        saveBtn.disabled = true;
        try {
            const resp = await fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, analysis })
            });
            const payload = await resp.json();
            if (!resp.ok || !payload.ok) {
                throw new Error('Save failed.');
            }
            await refreshSavedIdeas();
            showModal("Success", "<p>Idea saved successfully!</p>");
        } catch (e) {
            console.error(e);
            alert('Failed to save idea locally.');
        } finally {
            saveBtn.disabled = false;
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

    function renderTechnology(data) {
        const analysis = (data && data.analysis && typeof data.analysis === 'object') ? data.analysis : (data || {});

        const trl = data.technology_readiness_level || analysis.technology_readiness_level || '--';
        document.getElementById('trlValue').innerText = trl;

        const missing = data.missing_technologies || analysis.missing_technologies;
        const list = document.getElementById('missingTechList');
        list.innerHTML = '';
        if (missing && Array.isArray(missing) && missing.length) {
            missing.forEach(item => {
                const li = document.createElement('li');
                li.innerText = item;
                list.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.innerText = 'No missing technologies detected.';
            list.appendChild(li);
        }
    }

    function renderResearchPapers(papers) {
        const list = document.getElementById('researchPapersList');
        list.innerHTML = '';
        if (!papers || !Array.isArray(papers) || papers.length === 0) {
            const li = document.createElement('li');
            li.innerText = 'No papers found (API may be unavailable).';
            list.appendChild(li);
            return;
        }
        papers.forEach(p => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.href = p.url || '#';
            const year = (p.year !== undefined && p.year !== null) ? ` (${p.year})` : '';
            a.innerText = `${p.title || 'Untitled'}${year} — ${p.authors || 'Unknown'}`;
            li.appendChild(a);
            list.appendChild(li);
        });
    }

    function renderPatents(patents) {
        const list = document.getElementById('patentsList');
        list.innerHTML = '';
        if (!patents || !Array.isArray(patents) || patents.length === 0) {
            const li = document.createElement('li');
            li.innerText = 'No patents found.';
            list.appendChild(li);
            return;
        }
        patents.forEach(p => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.href = p.url || '#';
            a.innerText = p.title || 'Patent result';
            li.appendChild(a);
            list.appendChild(li);
        });
    }

    function renderCompanies(companies) {
        const list = document.getElementById('companiesList');
        list.innerHTML = '';
        if (!companies || !Array.isArray(companies) || companies.length === 0) {
            const li = document.createElement('li');
            li.innerText = 'No companies detected.';
            list.appendChild(li);
            return;
        }
        companies.forEach(name => {
            const li = document.createElement('li');
            li.innerText = name;
            list.appendChild(li);
        });
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

    function renderIssues(issues) {
        const list = document.getElementById('issuesList');
        if (!list) return;

        list.innerHTML = '';
        if (!issues || !Array.isArray(issues) || issues.length === 0) {
            const li = document.createElement('li');
            li.innerText = 'No issues detected for this run.';
            list.appendChild(li);
            return;
        }

        issues.forEach(issue => {
            const li = document.createElement('li');
            li.innerText = issue;
            list.appendChild(li);
        });
    }

    async function refreshSavedIdeas() {
        const list = document.getElementById('savedIdeasList');
        if (!list) return;
        list.innerHTML = '';
        try {
            const resp = await fetch('/saved');
            const data = await resp.json();
            const items = data.items || [];
            if (!Array.isArray(items) || items.length === 0) {
                const li = document.createElement('li');
                li.innerText = 'No saved ideas yet.';
                list.appendChild(li);
                return;
            }

            items.forEach(item => {
                const li = document.createElement('li');
                const topic = item.topic || 'Untitled';
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'saved-content';
                contentDiv.innerText = topic;

                const meta = document.createElement('div');
                meta.className = 'saved-meta';
                meta.innerText = item.timestamp ? `Saved: ${new Date(item.timestamp).toLocaleString()}` : '';
                contentDiv.appendChild(meta);
                
                contentDiv.addEventListener('click', () => {
                    const ans = item.analysis || {};
                    const prob = ans.revival_probability !== undefined ? `${ans.revival_probability}%` : '--%';
                    const feas = ans.feasibility_score !== undefined ? `${ans.feasibility_score}/10` : '--/10';
                    const imp = ans.impact_score !== undefined ? `${ans.impact_score}/10` : '--/10';
                    const ideaText = ans.idea || 'No description available.';
                    
                    const html = `
                        <div class="metrics-row" style="margin-bottom:15px;">
                            <span class="modal-metric">Probability: ${prob}</span>
                            <span class="modal-metric">Feasibility: ${feas}</span>
                            <span class="modal-metric">Impact: ${imp}</span>
                        </div>
                        <p><strong>Idea:</strong> ${ideaText}</p>
                    `;
                    showModal(topic, html);
                });

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn';
                deleteBtn.innerHTML = '🗑️';
                deleteBtn.title = "Delete Idea";
                deleteBtn.onclick = async (e) => {
                    e.stopPropagation();
                    if(confirm("Delete this idea?")) {
                       try {
                           const res = await fetch(`/saved/${item.id}`, { method: 'DELETE' });
                           if (res.ok) {
                               refreshSavedIdeas();
                           } else {
                               alert('Failed to delete idea.');
                           }
                       } catch (err) {
                           console.error(err);
                       }
                    }
                };
                
                li.appendChild(contentDiv);
                li.appendChild(deleteBtn);
                list.appendChild(li);
            });
        } catch (e) {
            const li = document.createElement('li');
            li.innerText = 'Failed to load saved ideas.';
            list.appendChild(li);
        }
    }

    // Load saved ideas on initial page load
    refreshSavedIdeas();
});
