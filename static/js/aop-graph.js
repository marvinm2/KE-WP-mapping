/**
 * AOP Network Graph — Standalone Adapter
 * Consumes AOPGraphCore (aop-graph-core.js) for all graph rendering logic.
 *
 * Handles page-specific concerns: card grid, Select2 dropdown, AOP selection
 * flow, side panel population, and KE redirect — all specific to /aop-network.
 *
 * Requires: aop-graph-core.js loaded before this script.
 */
var AOPGraph = (function () {
    'use strict';

    // Private state
    var cy = null;
    var kerData = null;
    var currentAOP = null;
    var selectedKEId = null;
    var geneCountMap = {};

    // ---------------------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------------------
    function init() {
        AOPGraphCore.resolveNodeColors();
        wireBackButton();
        wireCloseButton();
        loadData();
    }

    function loadData() {
        fetch('/api/ker-adjacency')
            .then(function (resp) {
                if (!resp.ok) {
                    throw new Error('HTTP ' + resp.status);
                }
                return resp.json();
            })
            .then(function (data) {
                kerData = data;
                populateSelect2(data);
                populateCardGrid(data);
                loadGeneCountMap(function () {
                    // gene count data ready — will be applied on each graph render
                });
            })
            .catch(function (err) {
                var grid = document.getElementById('aop-card-grid');
                if (grid) {
                    grid.innerHTML =
                        '<div class="aop-card-loading" style="color:#c0392b;">' +
                        'Failed to load AOP data. Please try refreshing the page.<br>' +
                        '<small>' + err.message + '</small></div>';
                }
                console.error('[AOPGraph] Failed to load /api/ker-adjacency:', err);
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
            header.appendChild(arrow);
            header.appendChild(typeBadge);
            header.appendChild(nameSpan);
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
        fetch('/api/ke-gene-counts')
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

    // ---------------------------------------------------------------------------
    // Card grid population
    // ---------------------------------------------------------------------------
    function populateCardGrid(data) {
        var grid = document.getElementById('aop-card-grid');
        if (!grid) return;

        // Clear loading placeholder
        grid.innerHTML = '';

        var aopIds = Object.keys(data).filter(function (k) {
            return k !== '_metadata';
        });

        if (aopIds.length === 0) {
            grid.innerHTML = '<div class="aop-card-loading">No AOP data available.</div>';
            return;
        }

        var fragment = document.createDocumentFragment();

        aopIds.forEach(function (aopId) {
            var aop = data[aopId];
            var keCount = Array.isArray(aop.kes) ? aop.kes.length : 0;
            var card = document.createElement('div');
            card.className = 'aop-card';
            card.setAttribute('data-aop-id', aopId);
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            card.setAttribute('aria-label', 'View graph for ' + aopId);
            card.innerHTML =
                '<div class="aop-card__id">' + AOPGraphCore.escapeHtml(aopId) + '</div>' +
                '<div class="aop-card__title">' + AOPGraphCore.escapeHtml(aop.title || '') + '</div>' +
                '<div class="aop-card__ke-count">' + keCount + ' KE' + (keCount !== 1 ? 's' : '') + '</div>';

            card.addEventListener('click', function () {
                selectAOP(aopId);
            });
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    selectAOP(aopId);
                }
            });

            fragment.appendChild(card);
        });

        grid.appendChild(fragment);
    }

    // ---------------------------------------------------------------------------
    // Select2 AOP dropdown
    // ---------------------------------------------------------------------------
    function populateSelect2(data) {
        var aopIds = Object.keys(data).filter(function (k) {
            return k !== '_metadata';
        });

        var selectData = aopIds.map(function (aopId) {
            var aop = data[aopId];
            return {
                id: aopId,
                text: aopId + ' \u2014 ' + (aop.title || aopId)
            };
        });

        var $select = $('#aop-selector');
        if ($select.length === 0) return;

        // Destroy any existing Select2, re-init with data
        if ($select.data('select2')) {
            $select.select2('destroy');
        }

        $select.select2({
            placeholder: 'Search by AOP title or ID...',
            allowClear: true,
            width: '100%',
            data: selectData,
            dropdownCssClass: 'aop-selector-dropdown'
        });

        $select.on('select2:select', function (e) {
            var aopId = e.params.data.id;
            selectAOP(aopId);
        });

        $select.on('select2:clear', function () {
            showCardGrid();
        });
    }

    // ---------------------------------------------------------------------------
    // AOP selection flow
    // ---------------------------------------------------------------------------
    function selectAOP(aopId) {
        if (!kerData || !kerData[aopId]) {
            console.warn('[AOPGraph] Unknown AOP:', aopId);
            return;
        }

        currentAOP = aopId;

        // Update Select2 to reflect selection
        var $select = $('#aop-selector');
        if ($select.length && $select.data('select2')) {
            $select.val(aopId).trigger('change.select2');
        }

        // Hide card grid, show graph section
        var cardSection = document.getElementById('aop-card-grid-section');
        var graphSection = document.getElementById('aop-graph-section');
        if (cardSection) cardSection.style.display = 'none';
        if (graphSection) graphSection.style.display = '';

        // Dismiss any open side panel before rendering new graph
        dismissSidePanel();

        // Render graph (must happen AFTER container is visible — see lazy Cytoscape init note)
        renderGraph(aopId);
    }

    // ---------------------------------------------------------------------------
    // Back to card grid
    // ---------------------------------------------------------------------------
    function showCardGrid() {
        // Destroy existing Cytoscape instance to free memory
        if (cy) {
            cy.destroy();
            cy = null;
        }

        currentAOP = null;
        selectedKEId = null;

        dismissSidePanel();

        // Reset Select2
        var $select = $('#aop-selector');
        if ($select.length && $select.data('select2')) {
            $select.val(null).trigger('change.select2');
        }

        var cardSection = document.getElementById('aop-card-grid-section');
        var graphSection = document.getElementById('aop-graph-section');
        if (graphSection) graphSection.style.display = 'none';
        if (cardSection) cardSection.style.display = '';
    }

    function wireBackButton() {
        var btn = document.getElementById('aop-back-btn');
        if (btn) {
            btn.addEventListener('click', showCardGrid);
        }
    }

    // ---------------------------------------------------------------------------
    // Graph rendering — delegates to AOPGraphCore
    // ---------------------------------------------------------------------------
    function renderGraph(aopId) {
        var aopData = kerData[aopId];
        if (!aopData) return;

        // Destroy previous instance if any
        if (cy) {
            cy.destroy();
            cy = null;
        }

        // Standalone page does not pass mappedKeIds — no mapping-status borders
        cy = AOPGraphCore.renderGraph('cy', aopData, {
            onNodeTap: function (nodeData, cyInst) {
                cyInst.elements().removeClass('active-node');
                cyInst.$('#' + nodeData.id).addClass('active-node');
                showSidePanel(nodeData);
            },
            onBackgroundTap: function () {
                dismissSidePanel();
            }
        });

        // Apply gene-count badges
        if (cy && Object.keys(geneCountMap).length > 0) {
            AOPGraphCore.applyGeneBadges(cy, geneCountMap);
        }
    }

    // ---------------------------------------------------------------------------
    // Side panel
    // ---------------------------------------------------------------------------
    function showSidePanel(nodeData) {
        var panel = document.getElementById('ke-side-panel');
        if (!panel) return;

        selectedKEId = nodeData.id;

        // Populate type badge
        var typeEl = document.getElementById('ke-panel-type');
        if (typeEl) {
            var type = nodeData.type || 'KE';
            var typeClass = 'ke-side-panel__ke-type ke-side-panel__ke-type--' + type.toLowerCase();
            typeEl.className = typeClass;
            typeEl.textContent = type;
        }

        // Populate title
        var titleEl = document.getElementById('ke-panel-title');
        if (titleEl) {
            titleEl.textContent = nodeData.label || nodeData.id;
        }

        // Populate ID
        var idEl = document.getElementById('ke-panel-id');
        if (idEl) {
            idEl.textContent = nodeData.id;
        }

        // Populate "Also in these AOPs" list
        var listEl = document.getElementById('ke-panel-aop-list');
        if (listEl && kerData) {
            var otherAOPs = AOPGraphCore.findAOPsForKE(nodeData.id, currentAOP, kerData);
            listEl.innerHTML = '';
            if (otherAOPs.length === 0) {
                var li = document.createElement('li');
                li.textContent = 'This KE is not in any other AOPs.';
                li.style.color = '#888';
                li.style.fontStyle = 'italic';
                listEl.appendChild(li);
            } else {
                otherAOPs.forEach(function (aopId) {
                    var li = document.createElement('li');
                    li.textContent = aopId;
                    if (kerData[aopId] && kerData[aopId].title) {
                        li.title = kerData[aopId].title;
                    }
                    listEl.appendChild(li);
                });
            }
        }

        // Populate gene list section (grouped by WP/GO term)
        var geneListEl = document.getElementById('ke-panel-gene-list');
        var geneLoadingEl = document.getElementById('ke-panel-gene-loading');
        if (geneListEl) {
            geneListEl.innerHTML = '';
            var count = geneCountMap[nodeData.id] || 0;
            if (count > 0 && geneLoadingEl) {
                geneLoadingEl.textContent = 'Loading ' + count + ' gene(s)...';
                geneLoadingEl.style.display = '';
                fetch('/api/ke-genes/' + encodeURIComponent(nodeData.id))
                    .then(function (resp) { return resp.ok ? resp.json() : { genes: [], groups: [] }; })
                    .then(function (data) {
                        geneLoadingEl.style.display = 'none';
                        var groups = data.groups || [];
                        if (groups.length > 0) {
                            renderGeneGroups(geneListEl, groups);
                        } else {
                            var li = document.createElement('li');
                            li.textContent = 'No mapped genes';
                            li.style.color = '#888';
                            li.style.fontStyle = 'italic';
                            geneListEl.appendChild(li);
                        }
                    })
                    .catch(function () {
                        geneLoadingEl.style.display = 'none';
                    });
            } else {
                if (geneLoadingEl) geneLoadingEl.style.display = 'none';
                var li = document.createElement('li');
                li.textContent = 'No mapped genes';
                li.style.color = '#888';
                li.style.fontStyle = 'italic';
                geneListEl.appendChild(li);
            }
        }

        // Wire Select this KE button
        var selectBtn = document.getElementById('ke-panel-select-btn');
        if (selectBtn) {
            // Replace the button to clear any previous listener
            var newBtn = selectBtn.cloneNode(true);
            selectBtn.parentNode.replaceChild(newBtn, selectBtn);
            newBtn.addEventListener('click', function () {
                redirectToKE(nodeData.id);
            });
        }

        // Open panel
        panel.classList.add('ke-side-panel--open');
    }

    function dismissSidePanel() {
        var panel = document.getElementById('ke-side-panel');
        if (panel) {
            panel.classList.remove('ke-side-panel--open');
        }
        selectedKEId = null;
        if (cy) {
            cy.elements().removeClass('active-node');
        }
    }

    function wireCloseButton() {
        var closeBtn = document.getElementById('ke-side-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                dismissSidePanel();
            });
        }
    }

    // ---------------------------------------------------------------------------
    // KE selection redirect
    // ---------------------------------------------------------------------------
    function redirectToKE(keId) {
        window.location.href = '/?ke_id=' + encodeURIComponent(keId);
    }

    // Public API
    return { init: init };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    AOPGraph.init();
});
