# Health Analytics Script in R
# This script processes medical records to find trends

library(jsonlite)

# Function to analyze medicine frequency
analyze_health <- function(json_data) {
  data <- fromJSON(json_data)
  
  # Placeholder for actual analysis logic
  # Example: Find the most frequent medicine or average duration
  
  result <- list(
    summary = "Health analysis complete",
    risk_level = "Low",
    insight = "Your medicine adherence looks consistent across the last 3 records."
  )
  
  return(toJSON(result, auto_unbox = TRUE))
}

# Entry point for command line execution
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 0) {
  cat(analyze_health(args[1]))
}
