/**
 * AOPGraphCore — Shared IIFE module for AOP graph rendering.
 *
 * Provides: resolveNodeColors, renderGraph, buildCytoscapeStyle, buildElements,
 *           findAOPsForKE, escapeHtml
 *
 * Consumed by:
 *   - aop-graph.js (standalone /aop-network adapter)
 *   - Future inline mapper adapter (Plan 02)
 *
 * Requires: Cytoscape.js to be loaded before this module.
 */
var AOPGraphCore = (function () {
    'use strict';

    // Register cytoscape-node-html-label plugin if available (CDN-loaded)
    if (typeof cytoscape !== 'undefined' && typeof cytoscapeNodeHtmlLabel !== 'undefined') {
        cytoscape.use(cytoscapeNodeHtmlLabel);
    }

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

    /**
     * Resolve NODE_COLORS and EDGE_COLOR from CSS custom properties.
     * Must be called after DOM is ready (usually in an adapter's init()).
     */
    function resolveNodeColors() {
        var mie  = getCSSVar('--color-primary-pink');
        var ke   = getCSSVar('--color-primary-blue');
        var ao   = getCSSVar('--color-secondary-teal');
        var edge = getCSSVar('--color-primary-dark');
        if (mie)  NODE_COLORS.MIE = mie;
        if (ke)   NODE_COLORS.KE  = ke;
        if (ao)   NODE_COLORS.AO  = ao;
        if (edge) EDGE_COLOR      = edge;
    }

    // ---------------------------------------------------------------------------
    // Style builder
    // ---------------------------------------------------------------------------

    /**
     * Build the Cytoscape style array.
     *
     * @param {Object} [options]
     * @param {Set}    [options.mappedKeIds]  When provided, add mapped/unmapped border selectors.
     * @returns {Array} Cytoscape style array
     */
    function buildCytoscapeStyle(options) {
        var styles = [
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

        // Optional mapping-status border indicators
        if (options && options.mappedKeIds) {
            styles.push({
                selector: 'node[?mapped]',
                style: {
                    'border-width': 4,
                    'border-color': '#2ecc71',
                    'border-style': 'solid'
                }
            });
            styles.push({
                selector: 'node[!mapped]',
                style: {
                    'border-width': 2,
                    'border-color': '#ccc',
                    'border-style': 'dashed'
                }
            });
        }

        return styles;
    }

    // ---------------------------------------------------------------------------
    // Element builder
    // ---------------------------------------------------------------------------

    /**
     * Build the Cytoscape elements array from an AOP entry.
     *
     * @param {Object} aopData      Single AOP entry from ker_adjacency JSON ({ kes, kers, title, ... })
     * @param {Set}    [mappedKeIds] When provided, sets data.mapped = true/false on each node element.
     * @returns {Array} Cytoscape elements array
     */
    function buildElements(aopData, mappedKeIds) {
        var elements = [];

        var kes = Array.isArray(aopData.kes) ? aopData.kes : [];
        kes.forEach(function (ke) {
            var nodeData = {
                id: ke.id,
                label: ke.title || ke.id,
                type: ke.type || 'KE'
            };
            if (mappedKeIds) {
                nodeData.mapped = mappedKeIds.has(ke.id);
            }
            elements.push({ data: nodeData });
        });

        var kers = Array.isArray(aopData.kers) ? aopData.kers : [];
        kers.forEach(function (ker, idx) {
            elements.push({
                data: {
                    id: 'ker-' + idx,
                    source: ker.upstream,
                    target: ker.downstream
                }
            });
        });

        return elements;
    }

    // ---------------------------------------------------------------------------
    // Graph renderer
    // ---------------------------------------------------------------------------

    /**
     * Create (or replace) a Cytoscape instance on the given container.
     *
     * @param {string} containerId  DOM id of the Cytoscape container element
     * @param {Object} aopData      Single AOP entry ({ kes, kers, title, ... })
     * @param {Object} [options]
     * @param {Set}              [options.mappedKeIds]    Passed to buildElements and buildCytoscapeStyle
     * @param {Function}         [options.onNodeTap]     Called with (nodeData, cyInstance) on node tap
     * @param {Function}         [options.onBackgroundTap] Called on tap on background
     * @param {Object}           [options.layoutOptions] Merged into the dagre layout config
     * @returns {Object} The Cytoscape instance (cy)
     */
    function renderGraph(containerId, aopData, options) {
        options = options || {};

        var container = document.getElementById(containerId);
        if (!container) {
            console.warn('[AOPGraphCore] Container not found:', containerId);
            return null;
        }

        // Destroy any previous Cytoscape instance on this container
        if (container._cy) {
            container._cy.destroy();
            container._cy = null;
        }

        var elements = buildElements(aopData, options.mappedKeIds || null);

        var layoutDefaults = {
            name: 'dagre',
            rankDir: 'LR',
            padding: 30,
            nodeSep: 50,
            rankSep: 100,
            animate: false
        };

        var layoutOptions = Object.assign({}, layoutDefaults, options.layoutOptions || {});

        var cy = cytoscape({
            container: container,
            elements: elements,
            style: buildCytoscapeStyle({ mappedKeIds: options.mappedKeIds || null }),
            layout: layoutOptions,
            userPanningEnabled: true,
            userZoomingEnabled: true,
            boxSelectionEnabled: false,
            maxZoom: 3,
            minZoom: 0.3
        });

        cy.on('layoutstop', function () {
            cy.fit(undefined, 30);
        });
        cy.fit(undefined, 30);
        cy.resize();

        // Wire tap events
        if (typeof options.onNodeTap === 'function') {
            cy.on('tap', 'node', function (evt) {
                var node = evt.target;
                cy.elements().removeClass('active-node');
                node.addClass('active-node');
                options.onNodeTap(node.data(), cy);
            });
        }

        if (typeof options.onBackgroundTap === 'function') {
            cy.on('tap', function (evt) {
                if (evt.target === cy) {
                    options.onBackgroundTap(cy);
                }
            });
        }

        // Store reference on container for cleanup on next call
        container._cy = cy;

        return cy;
    }

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    /**
     * Find all AOP IDs that contain a given KE ID, excluding the specified AOP.
     *
     * @param {string} keId         KE ID to look up
     * @param {string} excludeAopId AOP ID to exclude (usually the currently-shown AOP)
     * @param {Object} kerData      Full ker_adjacency data object
     * @returns {string[]} Matching AOP IDs
     */
    function findAOPsForKE(keId, excludeAopId, kerData) {
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
     *
     * @param {string} str
     * @returns {string}
     */
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * Apply gene-count badge overlays to graph nodes via cytoscape-node-html-label.
     * Call AFTER renderGraph() returns a cy instance.
     *
     * @param {Object} cy            Cytoscape instance
     * @param {Object} geneCountMap  {ke_id: count} — only KEs with genes
     */
    function applyGeneBadges(cy, geneCountMap) {
        if (!cy || !geneCountMap) return;
        if (typeof cy.nodeHtmlLabel !== 'function') {
            console.warn('[AOPGraphCore] nodeHtmlLabel not available — badge plugin not loaded');
            return;
        }
        cy.nodeHtmlLabel([{
            query: 'node',
            halign: 'right',
            valign: 'top',
            halignBox: 'left',
            valignBox: 'bottom',
            cssClass: 'gene-badge-container',
            tpl: function(data) {
                var count = geneCountMap[data.id];
                if (!count || count === 0) return '';
                return '<div class="gene-badge">' + escapeHtml(String(count)) + '</div>';
            }
        }]);
    }

    // ---------------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------------
    return {
        resolveNodeColors: resolveNodeColors,
        renderGraph: renderGraph,
        buildCytoscapeStyle: buildCytoscapeStyle,
        buildElements: buildElements,
        findAOPsForKE: findAOPsForKE,
        escapeHtml: escapeHtml,
        applyGeneBadges: applyGeneBadges
    };
})();
