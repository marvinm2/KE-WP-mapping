# R Examples for KE-WP Mapping Dataset
# Demonstrates various ways to access and analyze the dataset using R

# Required libraries
required_packages <- c("httr", "jsonlite", "dplyr", "ggplot2", "readr", 
                      "arrow", "DT", "plotly", "corrplot", "RColorBrewer")

# Install missing packages
missing_packages <- required_packages[!required_packages %in% installed.packages()[,"Package"]]
if(length(missing_packages)) {
  cat("Installing missing packages:", paste(missing_packages, collapse = ", "), "\n")
  install.packages(missing_packages)
}

# Load libraries
library(httr)
library(jsonlite)
library(dplyr)
library(ggplot2)
library(readr)
library(arrow)
library(DT)
library(plotly)
library(corrplot)
library(RColorBrewer)

# KE-WP Dataset Client Class
KEWPClient <- setRefClass("KEWPClient",
  fields = list(
    base_url = "character"
  ),
  
  methods = list(
    initialize = function(base_url = "https://ke-wp-mapping.org") {
      .self$base_url <- sub("/$", "", base_url)
    },
    
    get_mappings = function(...) {
      params <- list(...)
      url <- paste0(.self$base_url, "/api/v1/mappings")
      response <- GET(url, query = params)
      
      if (status_code(response) != 200) {
        stop("API request failed with status ", status_code(response))
      }
      
      return(fromJSON(content(response, "text")))
    },
    
    get_mapping = function(mapping_id) {
      url <- paste0(.self$base_url, "/api/v1/mappings/", mapping_id)
      response <- GET(url)
      
      if (status_code(response) != 200) {
        stop("API request failed with status ", status_code(response))
      }
      
      return(fromJSON(content(response, "text")))
    },
    
    search_mappings = function(query, ...) {
      params <- list(search = query, ...)
      return(.self$get_mappings(!!!params))
    },
    
    get_statistics = function() {
      url <- paste0(.self$base_url, "/api/v1/mappings/stats")
      response <- GET(url)
      
      if (status_code(response) != 200) {
        stop("API request failed with status ", status_code(response))
      }
      
      return(fromJSON(content(response, "text")))
    },
    
    export_data = function(format_name, ...) {
      params <- list(...)
      url <- paste0(.self$base_url, "/export/", format_name)
      response <- GET(url, query = params)
      
      if (status_code(response) != 200) {
        stop("Export request failed with status ", status_code(response))
      }
      
      return(response)
    },
    
    get_all_mappings = function(per_page = 100) {
      all_mappings <- list()
      page <- 1
      
      repeat {
        data <- .self$get_mappings(page = page, per_page = per_page)
        all_mappings <- append(all_mappings, list(data$data))
        
        if (!data$pagination$has_next) break
        page <- page + 1
      }
      
      return(bind_rows(all_mappings))
    }
  )
)

# Example 1: Basic Data Access
basic_data_access <- function() {
  cat("=== Example 1: Basic Data Access ===\n")
  
  client <- KEWPClient$new()
  
  # Get first page of mappings
  data <- client$get_mappings(per_page = 20)
  mappings <- data$data
  pagination <- data$pagination
  
  cat("Retrieved", nrow(mappings), "mappings (page 1 of", pagination$pages, ")\n")
  cat("Total mappings in dataset:", pagination$total, "\n")
  
  # Display first few mappings
  for (i in 1:min(3, nrow(mappings))) {
    mapping <- mappings[i, ]
    cat("\nMapping", i, ":\n")
    cat("  KE:", mapping$ke_id, "-", mapping$ke_title, "\n")
    cat("  WP:", mapping$wp_id, "-", mapping$wp_title, "\n")
    cat("  Confidence:", mapping$confidence_level, "\n")
    cat("  Connection:", mapping$connection_type, "\n")
  }
}

# Example 2: Filtering and Search
filtering_and_search <- function() {
  cat("\n=== Example 2: Filtering and Search ===\n")
  
  client <- KEWPClient$new()
  
  # Search for oxidative stress related mappings
  oxidative_results <- client$search_mappings("oxidative stress", per_page = 10)
  cat("Found", nrow(oxidative_results$data), "mappings related to 'oxidative stress'\n")
  
  # Filter by high confidence causative relationships
  high_conf_results <- client$get_mappings(
    confidence_level = "high",
    connection_type = "causative",
    per_page = 20
  )
  cat("Found", nrow(high_conf_results$data), "high-confidence causative mappings\n")
  
  # Filter by date range (last 30 days)
  date_30_days_ago <- Sys.Date() - 30
  recent_results <- client$get_mappings(
    created_after = paste0(date_30_days_ago, "T00:00:00Z"),
    per_page = 20
  )
  cat("Found", nrow(recent_results$data), "mappings created in the last 30 days\n")
}

# Example 3: Data Export
data_export_examples <- function() {
  cat("\n=== Example 3: Data Export ===\n")
  
  client <- KEWPClient$new()
  
  # Export as JSON
  json_response <- client$export_data("json", metadata = "true", provenance = "true")
  json_content <- content(json_response, "text")
  writeLines(json_content, "ke_wp_dataset.json")
  cat("Saved comprehensive JSON export to 'ke_wp_dataset.json'\n")
  
  # Export as Parquet
  tryCatch({
    parquet_response <- client$export_data("parquet", include_metadata_columns = "true")
    writeBin(content(parquet_response, "raw"), "ke_wp_dataset.parquet")
    cat("Saved Parquet export to 'ke_wp_dataset.parquet'\n")
  }, error = function(e) {
    cat("Parquet export failed:", e$message, "\n")
  })
  
  # Export as CSV (using existing download endpoint)
  csv_response <- GET(paste0(client$base_url, "/download"))
  if (status_code(csv_response) == 200) {
    writeLines(content(csv_response, "text"), "ke_wp_dataset.csv")
    cat("Saved CSV export to 'ke_wp_dataset.csv'\n")
  }
}

# Example 4: Data Analysis with dplyr
dplyr_analysis <- function() {
  cat("\n=== Example 4: Data Analysis with dplyr ===\n")
  
  client <- KEWPClient$new()
  
  # Get all data
  df <- client$get_all_mappings()
  
  cat("Dataset shape:", nrow(df), "rows x", ncol(df), "columns\n")
  cat("Columns:", paste(names(df), collapse = ", "), "\n")
  
  # Basic statistics using dplyr
  cat("\nConfidence Level Distribution:\n")
  confidence_dist <- df %>%
    count(confidence_level, sort = TRUE) %>%
    mutate(percentage = round(n / sum(n) * 100, 1))
  print(confidence_dist)
  
  cat("\nConnection Type Distribution:\n")
  connection_dist <- df %>%
    count(connection_type, sort = TRUE) %>%
    mutate(percentage = round(n / sum(n) * 100, 1))
  print(connection_dist)
  
  # Top contributors
  cat("\nTop 10 Contributors:\n")
  top_contributors <- df %>%
    filter(!is.na(created_by) & created_by != "") %>%
    count(created_by, sort = TRUE) %>%
    head(10)
  print(top_contributors)
  
  # Temporal analysis
  if ("created_at" %in% names(df)) {
    df$created_date <- as.Date(substr(df$created_at, 1, 10))
    df$created_month <- format(df$created_date, "%Y-%m")
    
    cat("\nMonthly Creation Counts:\n")
    monthly_counts <- df %>%
      filter(!is.na(created_date)) %>%
      count(created_month, sort = TRUE) %>%
      head(10)
    print(monthly_counts)
  }
  
  return(df)
}

# Example 5: Visualization with ggplot2
visualization_examples <- function(df = NULL) {
  cat("\n=== Example 5: Data Visualization ===\n")
  
  if (is.null(df)) {
    client <- KEWPClient$new()
    df <- client$get_all_mappings()
  }
  
  # Create visualizations
  
  # 1. Confidence Level Distribution
  p1 <- df %>%
    count(confidence_level) %>%
    mutate(confidence_level = factor(confidence_level, levels = c("low", "medium", "high"))) %>%
    ggplot(aes(x = confidence_level, y = n, fill = confidence_level)) +
    geom_bar(stat = "identity") +
    scale_fill_brewer(type = "qual", palette = "Set2") +
    labs(title = "Confidence Level Distribution",
         x = "Confidence Level",
         y = "Number of Mappings",
         fill = "Confidence") +
    theme_minimal() +
    theme(legend.position = "none")
  
  # 2. Connection Type Distribution  
  p2 <- df %>%
    count(connection_type) %>%
    ggplot(aes(x = reorder(connection_type, n), y = n, fill = connection_type)) +
    geom_bar(stat = "identity") +
    coord_flip() +
    scale_fill_brewer(type = "qual", palette = "Set1") +
    labs(title = "Connection Type Distribution",
         x = "Connection Type",
         y = "Number of Mappings",
         fill = "Connection") +
    theme_minimal() +
    theme(legend.position = "none")
  
  # 3. Confidence vs Connection Type Heatmap
  p3 <- df %>%
    count(confidence_level, connection_type) %>%
    mutate(confidence_level = factor(confidence_level, levels = c("low", "medium", "high"))) %>%
    ggplot(aes(x = connection_type, y = confidence_level, fill = n)) +
    geom_tile() +
    scale_fill_gradient(low = "white", high = "darkblue") +
    labs(title = "Confidence vs Connection Type Heatmap",
         x = "Connection Type",
         y = "Confidence Level",
         fill = "Count") +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  
  # 4. Top Contributors
  p4 <- df %>%
    filter(!is.na(created_by) & created_by != "") %>%
    count(created_by, sort = TRUE) %>%
    head(10) %>%
    ggplot(aes(x = reorder(created_by, n), y = n)) +
    geom_bar(stat = "identity", fill = "steelblue") +
    coord_flip() +
    labs(title = "Top 10 Contributors",
         x = "Contributor",
         y = "Number of Mappings") +
    theme_minimal()
  
  # Save plots
  ggsave("confidence_distribution.png", p1, width = 8, height = 6, dpi = 300)
  ggsave("connection_distribution.png", p2, width = 8, height = 6, dpi = 300)
  ggsave("confidence_connection_heatmap.png", p3, width = 8, height = 6, dpi = 300)
  ggsave("top_contributors.png", p4, width = 10, height = 6, dpi = 300)
  
  cat("Saved visualizations:\n")
  cat("- confidence_distribution.png\n")
  cat("- connection_distribution.png\n") 
  cat("- confidence_connection_heatmap.png\n")
  cat("- top_contributors.png\n")
  
  # Display plots
  print(p1)
  print(p2)
  print(p3)
  print(p4)
}

# Example 6: Interactive Visualizations with plotly
interactive_visualizations <- function(df = NULL) {
  cat("\n=== Example 6: Interactive Visualizations ===\n")
  
  if (is.null(df)) {
    client <- KEWPClient$new()
    df <- client$get_all_mappings()
  }
  
  # Interactive scatter plot
  if ("created_at" %in% names(df)) {
    df$created_date <- as.Date(substr(df$created_at, 1, 10))
    df$ke_title_length <- nchar(df$ke_title)
    df$wp_title_length <- nchar(df$wp_title)
    
    p_scatter <- df %>%
      ggplot(aes(x = ke_title_length, y = wp_title_length, 
                 color = confidence_level, 
                 text = paste("KE:", ke_title, "<br>WP:", wp_title))) +
      geom_point(alpha = 0.7) +
      scale_color_brewer(type = "qual", palette = "Set1") +
      labs(title = "Title Lengths: Key Events vs Pathways",
           x = "Key Event Title Length",
           y = "WikiPathway Title Length",
           color = "Confidence") +
      theme_minimal()
    
    p_interactive <- ggplotly(p_scatter, tooltip = "text")
    
    # Save interactive plot
    htmlwidgets::saveWidget(p_interactive, "interactive_scatter.html")
    cat("Saved interactive scatter plot to 'interactive_scatter.html'\n")
  }
  
  # Interactive time series
  if ("created_date" %in% names(df)) {
    monthly_data <- df %>%
      filter(!is.na(created_date)) %>%
      mutate(month = format(created_date, "%Y-%m")) %>%
      count(month, confidence_level) %>%
      arrange(month)
    
    p_timeseries <- monthly_data %>%
      ggplot(aes(x = month, y = n, color = confidence_level, group = confidence_level)) +
      geom_line() +
      geom_point() +
      scale_color_brewer(type = "qual", palette = "Set1") +
      labs(title = "Mapping Creation Over Time by Confidence Level",
           x = "Month",
           y = "Number of Mappings",
           color = "Confidence") +
      theme_minimal() +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
    
    p_timeseries_interactive <- ggplotly(p_timeseries)
    
    # Save interactive time series
    htmlwidgets::saveWidget(p_timeseries_interactive, "interactive_timeseries.html")
    cat("Saved interactive time series to 'interactive_timeseries.html'\n")
  }
}

# Example 7: Advanced Analysis with Parquet
advanced_parquet_analysis <- function() {
  cat("\n=== Example 7: Advanced Parquet Analysis ===\n")
  
  tryCatch({
    # Read Parquet file if it exists
    if (file.exists("ke_wp_dataset.parquet")) {
      df <- read_parquet("ke_wp_dataset.parquet")
      cat("Loaded", nrow(df), "mappings from Parquet file\n")
      
      # Check for analytics columns
      analytics_cols <- names(df)[grepl("numeric|length|year|month", names(df))]
      cat("Analytics columns available:", paste(analytics_cols, collapse = ", "), "\n")
      
      # Correlation analysis if numeric columns exist
      numeric_cols <- names(df)[sapply(df, is.numeric)]
      if (length(numeric_cols) > 1) {
        cat("\nPerforming correlation analysis...\n")
        
        cor_matrix <- df %>%
          select(all_of(numeric_cols)) %>%
          cor(use = "complete.obs")
        
        # Create correlation plot
        png("correlation_matrix.png", width = 800, height = 600)
        corrplot(cor_matrix, method = "color", type = "upper", 
                 order = "hclust", tl.cex = 0.8, tl.col = "black")
        dev.off()
        
        cat("Saved correlation matrix to 'correlation_matrix.png'\n")
        print(round(cor_matrix, 3))
      }
      
    } else {
      cat("Parquet file not found. Run data export example first.\n")
    }
    
  }, error = function(e) {
    cat("Arrow package not available or error reading Parquet:", e$message, "\n")
    cat("Install arrow package with: install.packages('arrow')\n")
  })
}

# Example 8: Statistical Analysis
statistical_analysis <- function(df = NULL) {
  cat("\n=== Example 8: Statistical Analysis ===\n")
  
  if (is.null(df)) {
    client <- KEWPClient$new()
    df <- client$get_all_mappings()
  }
  
  # Chi-square test for independence
  if (nrow(df) > 0) {
    contingency_table <- table(df$confidence_level, df$connection_type)
    cat("Contingency Table - Confidence vs Connection:\n")
    print(contingency_table)
    
    # Chi-square test
    chi_test <- chisq.test(contingency_table)
    cat("\nChi-square test for independence:\n")
    cat("Chi-square statistic:", round(chi_test$statistic, 4), "\n")
    cat("p-value:", format.pval(chi_test$p.value), "\n")
    cat("Degrees of freedom:", chi_test$parameter, "\n")
    
    if (chi_test$p.value < 0.05) {
      cat("Result: Confidence level and connection type are significantly associated (p < 0.05)\n")
    } else {
      cat("Result: No significant association between confidence level and connection type (p >= 0.05)\n")
    }
  }
  
  # Summary statistics
  if ("created_at" %in% names(df)) {
    df$created_date <- as.Date(substr(df$created_at, 1, 10))
    
    cat("\nTemporal Summary:\n")
    cat("Date range:", as.character(min(df$created_date, na.rm = TRUE)), "to", 
        as.character(max(df$created_date, na.rm = TRUE)), "\n")
    cat("Average mappings per day:", round(nrow(df) / as.numeric(difftime(max(df$created_date, na.rm = TRUE), 
                                                                        min(df$created_date, na.rm = TRUE), units = "days")), 2), "\n")
  }
}

# Main function to run all examples
main <- function() {
  cat("KE-WP Mapping Dataset - R Examples\n")
  cat(paste(rep("=", 50), collapse = ""), "\n")
  
  tryCatch({
    # Run all examples
    basic_data_access()
    filtering_and_search()
    data_export_examples()
    df <- dplyr_analysis()
    visualization_examples(df)
    interactive_visualizations(df)
    advanced_parquet_analysis()
    statistical_analysis(df)
    
    cat("\n", paste(rep("=", 50), collapse = ""), "\n")
    cat("All examples completed successfully!\n")
    cat("Check the generated files:\n")
    cat("- ke_wp_dataset.json (comprehensive JSON export)\n")
    cat("- ke_wp_dataset.csv (CSV export)\n")
    cat("- ke_wp_dataset.parquet (analytics-ready format)\n")
    cat("- Various PNG visualization files\n")
    cat("- interactive_scatter.html (interactive plot)\n")
    cat("- interactive_timeseries.html (interactive time series)\n")
    
  }, error = function(e) {
    cat("Error running examples:", e$message, "\n")
    traceback()
  })
}

# Run examples if script is executed directly
if (sys.nframe() == 0) {
  main()
}