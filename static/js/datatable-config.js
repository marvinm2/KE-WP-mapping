/**
 * Shared DataTables Configuration
 * Centralizes common settings for all tables in the application
 */

const DataTableConfig = {
    /**
     * Base configuration for standard tables
     */
    base: {
        dom: 'Bfrtip',
        scrollX: true,
        paging: true,
        searching: true,
        info: true,
        autoWidth: false
    },

    /**
     * Configuration for tables with CSV/Excel/PDF export
     */
    withFullExport: {
        dom: 'Bfrtip',
        buttons: ['csvHtml5', 'excelHtml5', 'pdfHtml5', 'print'],
        scrollX: true,
        paging: true,
        searching: true,
        info: true,
        autoWidth: false
    },

    /**
     * Configuration for tables with basic CSV/Excel export only
     */
    withBasicExport: {
        dom: 'Bfrtip',
        buttons: ['csvHtml5', 'excelHtml5'],
        scrollX: true,
        paging: true,
        searching: true,
        info: true,
        pageLength: 20
    },

    /**
     * Utility: Truncate text with "Show more/Show less" toggle
     * Used by ke-details and pw-details tables
     */
    truncateWithToggle: function(data, type, row, maxLength = 200) {
        if (!data || type !== 'display') {
            return data || '';
        }

        if (data.length <= maxLength) {
            return data;
        }

        const truncated = data.substring(0, maxLength);
        const remaining = data.substring(maxLength);
        const uniqueId = 'desc_' + Math.random().toString(36).substr(2, 9);

        return `
            <span id="${uniqueId}_short">${truncated}...
                <a href="javascript:void(0)" onclick="toggleDescription('${uniqueId}')"
                   style="color: #307BBF; text-decoration: underline; cursor: pointer;">
                    Show more
                </a>
            </span>
            <span id="${uniqueId}_full" style="display: none;">${data}
                <a href="javascript:void(0)" onclick="toggleDescription('${uniqueId}')"
                   style="color: #307BBF; text-decoration: underline; cursor: pointer;">
                    Show less
                </a>
            </span>
        `;
    },

    /**
     * Utility: Merge base config with custom options
     */
    merge: function(baseConfig, customOptions) {
        return Object.assign({}, this[baseConfig], customOptions);
    }
};

/**
 * Toggle description visibility (used by truncateWithToggle)
 */
function toggleDescription(id) {
    const shortElem = document.getElementById(id + '_short');
    const fullElem = document.getElementById(id + '_full');

    if (shortElem.style.display === 'none') {
        shortElem.style.display = 'inline';
        fullElem.style.display = 'none';
    } else {
        shortElem.style.display = 'none';
        fullElem.style.display = 'inline';
    }
}
