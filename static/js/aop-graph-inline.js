/* ==========================================================================
   AOPGraphInline — Inline AOP graph adapter for the mapper page (index.html)
   IIFE module; depends on AOPGraphCore (aop-graph-core.js) and jQuery.
   ========================================================================== */

var AOPGraphInline = (function () {
    'use strict';

    var cy = null;
    var kerData = null;
    var mappedKeIds = new Set();
    var currentAOP = null;
    var currentTab = 'wp';
    var biolevelMap = {};
    var geneCountMap = {};
    var dataLoaded = false;

    function init() {
        AOPGraphCore.resolveNodeColors();
        currentTab = getActiveTab();
        wireAOPFilter();
        wireTabSwitcher();
    }

    function getActiveTab() {
        var activeTab = document.querySelector('.mapping-tab.active');
        return activeTab ? (activeTab.getAttribute('data-tab') || 'wp') : 'wp';
    }

    // --- AOP Filter hook ---
    function wireAOPFilter() {
        $('#aop_filter').on('change', function () {
            var aopId = $(this).val();
            if (!aopId) {
                hideInlineGraph();
            } else {
                showInlineGraph(aopId);
            }
        });
    }

    // --- Tab switcher hook ---
    function wireTabSwitcher() {
        $(document).on('click', '.mapping-tab', function () {
            var tab = $(this).data('tab');
            if (tab && tab !== currentTab) {
                currentTab = tab;
                if (currentAOP) {
                    var pending = 2;
                    var done = function () {
                        if (--pending === 0) {
                            renderInlineGraph(currentAOP);
                        }
                    };
                    loadMappedKeIds(currentTab, done);
                    loadGeneCountMap(done);
                }
            }
        });
    }

    // --- Data loading (lazy, on first AOP selection) ---
    function ensureData(callback) {
        if (dataLoaded && kerData) {
            callback();
            return;
        }
        fetch('/api/ker-adjacency')
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                kerData = data;
                dataLoaded = true;
                callback();
            })
            .catch(function (err) {
                console.error('[AOPGraphInline] Failed to load KER data:', err);
            });
    }

    function loadMappedKeIds(tab, callback) {
        fetch('/api/mapped-ke-ids?type=' + encodeURIComponent(tab))
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                mappedKeIds = new Set(data.ke_ids || []);
                callback();
            })
            .catch(function (err) {
                console.error('[AOPGraphInline] Failed to load mapped KE IDs:', err);
                mappedKeIds = new Set();
                callback();
            });
    }

    function loadBiolevels(callback) {
        if (Object.keys(biolevelMap).length > 0) {
            callback();
            return;
        }
        fetch('/api/ke-biolevels')
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                biolevelMap = data || {};
                callback();
            })
            .catch(function (err) {
                console.error('[AOPGraphInline] Failed to load biolevels:', err);
                callback();
            });
    }

    function renderGeneGroups(container, groups) {
        groups.forEach(function (group) {
            var div = document.createElement('div');
            div.className = 'gene-group';
            var header = document.createElement('div');
            header.className = 'gene-group__header';
            var arrow = document.createElement('span');
            arrow.className = 'gene-group__arrow';
            arrow.textContent = '\u25B6';
            var typeBadge = document.createElement('span');
            typeBadge.className = 'gene-group__type-badge gene-group__type-badge--' + group.type;
            typeBadge.textContent = group.type.toUpperCase();
            var nameSpan = document.createElement('span');
            nameSpan.textContent = group.name;
            nameSpan.style.flex = '1';
            nameSpan.style.overflow = 'hidden';
            nameSpan.style.textOverflow = 'ellipsis';
            nameSpan.style.whiteSpace = 'nowrap';
            nameSpan.title = group.name;
            var countSpan = document.createElement('span');
            countSpan.className = 'gene-group__count';
            countSpan.textContent = '(' + group.genes.length + ')';
            var confBadge = document.createElement('span');
            var level = (group.confidence_level || 'low').toLowerCase();
            confBadge.className = 'confidence-' + level;
            confBadge.textContent = level.charAt(0).toUpperCase() + level.slice(1);
            confBadge.style.fontSize = '11px';
            confBadge.style.marginLeft = '4px';
            header.appendChild(arrow);
            header.appendChild(typeBadge);
            header.appendChild(nameSpan);
            header.appendChild(confBadge);
            header.appendChild(countSpan);
            var ul = document.createElement('ul');
            ul.className = 'gene-group__genes';
            group.genes.forEach(function (symbol) {
                var li = document.createElement('li');
                var a = document.createElement('a');
                a.href = 'https://www.genecards.org/cgi-bin/carddisp.pl?gene=' + encodeURIComponent(symbol);
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                a.textContent = symbol;
                li.appendChild(a);
                ul.appendChild(li);
            });
            header.addEventListener('click', function () {
                div.classList.toggle('gene-group--open');
            });
            div.appendChild(header);
            div.appendChild(ul);
            container.appendChild(div);
        });
    }

    function loadGeneCountMap(callback) {
        fetch('/api/ke-gene-counts?type=' + encodeURIComponent(currentTab))
            .then(function (resp) { return resp.ok ? resp.json() : {}; })
            .then(function (data) {
                geneCountMap = data || {};
                callback();
            })
            .catch(function () {
                geneCountMap = {};
                callback();
            });
    }

    // --- Graph show/hide ---
    function showInlineGraph(aopId) {
        ensureData(function () {
            if (!kerData || !kerData[aopId]) {
                hideInlineGraph();
                return;
            }
            currentAOP = aopId;
            var pending = 3;
            var done = function () {
                if (--pending === 0) {
                    var panel = document.getElementById('aop-inline-graph-panel');
                    if (panel) panel.style.display = '';
                    renderInlineGraph(aopId);
                }
            };
            loadBiolevels(done);
            loadMappedKeIds(currentTab, done);
            loadGeneCountMap(done);
        });
    }

    function hideInlineGraph() {
        var panel = document.getElementById('aop-inline-graph-panel');
        if (panel) panel.style.display = 'none';
        hideInlineInfoPanel();
        if (cy) {
            cy.destroy();
            cy = null;
        }
        currentAOP = null;
    }

    // --- Graph rendering ---
    function renderInlineGraph(aopId) {
        var aopData = kerData[aopId];
        if (!aopData) return;

        // Destroy previous instance
        if (cy) {
            cy.destroy();
            cy = null;
        }

        hideInlineInfoPanel();

        cy = AOPGraphCore.renderGraph('cy-inline', aopData, {
            mappedKeIds: mappedKeIds,
            onNodeTap: function (nodeData) {
                cy.elements().removeClass('active-node');
                // Find the tapped node and add active-node class
                var tappedNode = cy.getElementById(nodeData.id);
                if (tappedNode) tappedNode.addClass('active-node');
                showInlineInfoPanel(nodeData);
            },
            onBackgroundTap: function () {
                hideInlineInfoPanel();
                if (cy) cy.elements().removeClass('active-node');
            },
            layoutOptions: {
                padding: 20,
                nodeSep: 40,
                rankSep: 80
            }
        });

        // Apply gene-count badges
        if (cy && Object.keys(geneCountMap).length > 0) {
            AOPGraphCore.applyGeneBadges(cy, geneCountMap);
        }
    }

    // --- Info panel ---
    function showInlineInfoPanel(nodeData) {
        var panel = document.getElementById('ke-inline-panel');
        if (!panel) return;

        // Type badge
        var typeEl = panel.querySelector('.ke-inline-panel__type');
        if (typeEl) {
            var type = nodeData.type || 'KE';
            typeEl.className = 'ke-inline-panel__type ke-side-panel__ke-type ke-side-panel__ke-type--' + type.toLowerCase();
            typeEl.textContent = type;
        }

        // Title
        var titleEl = panel.querySelector('.ke-inline-panel__title');
        if (titleEl) titleEl.textContent = nodeData.label || nodeData.id;

        // KE ID
        var idEl = panel.querySelector('.ke-inline-panel__id');
        if (idEl) idEl.textContent = nodeData.id;

        // Biological level
        var biolevelEl = panel.querySelector('.ke-inline-panel__biolevel');
        if (biolevelEl) {
            var level = biolevelMap[nodeData.id] || 'Unknown';
            biolevelEl.textContent = level;
        }

        // Mapping status indicator
        var statusEl = panel.querySelector('.ke-inline-panel__status');
        if (statusEl) {
            var isMapped = mappedKeIds.has(nodeData.id);
            statusEl.textContent = isMapped ? 'Mapped (' + currentTab.toUpperCase() + ')' : 'Not mapped (' + currentTab.toUpperCase() + ')';
            statusEl.className = 'ke-inline-panel__status ' + (isMapped ? 'ke-inline-panel__status--mapped' : 'ke-inline-panel__status--unmapped');
        }

        // Gene list section (grouped by WP/GO term)
        var geneSection = panel.querySelector('.ke-inline-panel__gene-section');
        if (geneSection) {
            var geneListEl = geneSection.querySelector('.ke-inline-panel__gene-list');
            var geneLoadingEl = geneSection.querySelector('.ke-inline-panel__gene-loading');
            if (geneListEl) geneListEl.innerHTML = '';
            var count = geneCountMap[nodeData.id] || 0;
            if (count > 0) {
                if (geneLoadingEl) {
                    geneLoadingEl.textContent = 'Loading ' + count + ' gene(s)...';
                    geneLoadingEl.style.display = '';
                }
                geneSection.style.display = '';
                fetch('/api/ke-genes/' + encodeURIComponent(nodeData.id) + '?type=' + encodeURIComponent(currentTab))
                    .then(function (resp) { return resp.ok ? resp.json() : { genes: [], groups: [] }; })
                    .then(function (data) {
                        if (geneLoadingEl) geneLoadingEl.style.display = 'none';
                        var groups = data.groups || [];
                        if (groups.length > 0) {
                            renderGeneGroups(geneListEl, groups);
                        }
                    })
                    .catch(function () {
                        if (geneLoadingEl) geneLoadingEl.style.display = 'none';
                    });
            } else {
                geneSection.style.display = 'none';
            }
        }

        // Wire "Use this KE" button
        var useBtn = panel.querySelector('.ke-inline-panel__use-btn');
        if (useBtn) {
            var newBtn = useBtn.cloneNode(true);
            useBtn.parentNode.replaceChild(newBtn, useBtn);
            newBtn.addEventListener('click', function () {
                useThisKE(nodeData.id);
            });
        }

        panel.style.display = '';
    }

    function hideInlineInfoPanel() {
        var panel = document.getElementById('ke-inline-panel');
        if (panel) panel.style.display = 'none';
    }

    // --- "Use this KE" action ---
    function useThisKE(keId) {
        hideInlineInfoPanel();

        var $keDropdown = $('#ke_id');

        // If the option doesn't exist in the current (possibly AOP-filtered) dropdown,
        // restore the full KE list so the option is available
        if ($keDropdown.find('option[value="' + keId + '"]').length === 0) {
            var app = window.KEWPApp;
            if (app && app.allKEOptions) {
                app.populateKEDropdown(app.allKEOptions);
                // Clear the AOP filter UI to stay consistent
                $('#aop_filter').val(null).trigger('change');
                $('#clear_aop_filter').hide();
            }
        }

        $keDropdown.val(keId).trigger('change');

        // Smooth scroll to the KE dropdown area
        var keContainer = document.querySelector('.dropdown-container');
        if (keContainer) {
            keContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    return { init: init };
})();

document.addEventListener('DOMContentLoaded', function () {
    // Delay init slightly to ensure main.js has populated KE dropdown
    setTimeout(function () {
        AOPGraphInline.init();
    }, 100);
});
