/**
 * AOP Network Graph Module
 * IIFE module for Cytoscape.js graph rendering, node interaction, side panel,
 * and KE selection on /aop-network.
 *
 * Fetches /api/ker-adjacency on init, populates card grid + Select2 dropdown,
 * renders interactive graphs per AOP, and handles KE selection redirect.
 */
var AOPGraph = (function () {
    'use strict';

    // Private state
    var cy = null;
    var kerData = null;
    var currentAOP = null;
    var selectedKEId = null;

    // Node color palette — resolved from CSS variables at init time
    // (Cytoscape style objects do not support CSS custom properties)
    var NODE_COLORS = { MIE: '#E6007E', KE: '#307BBF', AO: '#005A6C' };
    var EDGE_COLOR = '#29235C';

    // ---------------------------------------------------------------------------
    // CSS variable resolution
    // ---------------------------------------------------------------------------
    function getCSSVar(name) {
        var val = getComputedStyle(document.documentElement)
            .getPropertyValue(name)
            .trim();
        return val || undefined;
    }

    function resolveNodeColors() {
        var mie = getCSSVar('--color-primary-pink');
        var ke  = getCSSVar('--color-primary-blue');
        var ao  = getCSSVar('--color-secondary-teal');
        var edge = getCSSVar('--color-primary-dark');
        if (mie) NODE_COLORS.MIE = mie;
        if (ke)  NODE_COLORS.KE  = ke;
        if (ao)  NODE_COLORS.AO  = ao;
        if (edge) EDGE_COLOR     = edge;
    }

    // ---------------------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------------------
    function init() {
        resolveNodeColors();
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
                '<div class="aop-card__id">' + escapeHtml(aopId) + '</div>' +
                '<div class="aop-card__title">' + escapeHtml(aop.title || '') + '</div>' +
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
    // Graph rendering (Cytoscape.js + dagre)
    // ---------------------------------------------------------------------------
    function renderGraph(aopId) {
        var aop = kerData[aopId];
        if (!aop) return;

        // Destroy previous instance if any
        if (cy) {
            cy.destroy();
            cy = null;
        }

        var container = document.getElementById('cy');
        if (!container) return;

        // Build elements array
        var elements = [];

        var kes = Array.isArray(aop.kes) ? aop.kes : [];
        kes.forEach(function (ke) {
            elements.push({
                data: {
                    id: ke.id,
                    label: ke.title || ke.id,
                    type: ke.type || 'KE'
                }
            });
        });

        var kers = Array.isArray(aop.kers) ? aop.kers : [];
        kers.forEach(function (ker, idx) {
            elements.push({
                data: {
                    id: 'ker-' + idx,
                    source: ker.upstream,
                    target: ker.downstream
                }
            });
        });

        // Initialise Cytoscape AFTER container is visible
        cy = cytoscape({
            container: container,
            elements: elements,
            style: buildCytoscapeStyle(),
            layout: {
                name: 'dagre',
                rankDir: 'LR',
                padding: 30,
                nodeSep: 50,
                rankSep: 100,
                animate: false
            },
            userPanningEnabled: true,
            userZoomingEnabled: true,
            boxSelectionEnabled: false
        });

        cy.fit(undefined, 30);
        cy.resize();

        // Bind node tap
        cy.on('tap', 'node', function (evt) {
            var node = evt.target;
            cy.elements().removeClass('active-node');
            node.addClass('active-node');
            showSidePanel(node.data());
        });

        // Tap on background — dismiss panel
        cy.on('tap', function (evt) {
            if (evt.target === cy) {
                dismissSidePanel();
                cy.elements().removeClass('active-node');
            }
        });
    }

    function buildCytoscapeStyle() {
        return [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-wrap': 'wrap',
                    'text-max-width': '120px',
                    'font-size': '10px',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'width': 60,
                    'height': 60,
                    'shape': 'round-rectangle',
                    'color': '#fff',
                    'text-outline-width': 2,
                    'text-outline-color': '#333'
                }
            },
            {
                selector: 'node[type="MIE"]',
                style: {
                    'background-color': NODE_COLORS.MIE,
                    'text-outline-color': NODE_COLORS.MIE
                }
            },
            {
                selector: 'node[type="KE"]',
                style: {
                    'background-color': NODE_COLORS.KE,
                    'text-outline-color': NODE_COLORS.KE
                }
            },
            {
                selector: 'node[type="AO"]',
                style: {
                    'background-color': NODE_COLORS.AO,
                    'text-outline-color': NODE_COLORS.AO
                }
            },
            {
                selector: 'node.active-node',
                style: {
                    'border-width': 4,
                    'border-color': '#FFD700',
                    'border-style': 'solid',
                    'shadow-blur': 10,
                    'shadow-color': '#FFD700',
                    'shadow-opacity': 0.6
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': EDGE_COLOR,
                    'target-arrow-color': EDGE_COLOR,
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.2
                }
            }
        ];
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
            var otherAOPs = findAOPsForKE(nodeData.id, currentAOP);
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

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    /**
     * Find all AOP IDs that contain a given KE ID, excluding the current AOP.
     */
    function findAOPsForKE(keId, excludeAopId) {
        if (!kerData) return [];
        return Object.keys(kerData).filter(function (aopId) {
            if (aopId === '_metadata') return false;
            if (aopId === excludeAopId) return false;
            var aop = kerData[aopId];
            if (!Array.isArray(aop.kes)) return false;
            return aop.kes.some(function (ke) {
                return ke.id === keId;
            });
        });
    }

    /**
     * Minimal HTML escape to prevent XSS when setting innerHTML.
     */
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Public API
    return { init: init };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    AOPGraph.init();
});
