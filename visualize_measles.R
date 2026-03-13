library(tidyverse)
library(scales)

# ── Load data ────────────────────────────────────────────────────────────────

df <- read_csv("measles_structured.csv", na = "NA") |>
  mutate(snapshot_date = as.Date(snapshot_date)) |>
  # Drop duplicate update dates (keep first snapshot)
  distinct(update_date, .keep_all = TRUE)

# ── 1. Total cases over time ────────────────────────────────────────────────

ggplot(df |> filter(!is.na(total_cases)),
       aes(x = snapshot_date, y = total_cases)) +
  geom_line(linewidth = 0.8, color = "#1a5276") +
  geom_point(size = 1.5, color = "#1a5276") +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Cumulative Confirmed Measles Cases in the U.S.",
    subtitle = "Source: CDC Measles Cases and Outbreaks page",
    x = NULL, y = "Total confirmed cases"
  ) +
  theme_minimal(base_size = 13)

ggsave("plots/total_cases.png", width = 9, height = 5, dpi = 200)

# ── 2. Cases by age group (counts) ──────────────────────────────────────────

age_long <- df |>
  select(snapshot_date, age_under5_n, age_5_19_n, age_20plus_n) |>
  pivot_longer(-snapshot_date, names_to = "age_group", values_to = "cases") |>
  filter(!is.na(cases)) |>
  mutate(age_group = recode(age_group,
    "age_under5_n" = "Under 5",
    "age_5_19_n"   = "5-19",
    "age_20plus_n" = "20+"
  )) |>
  mutate(age_group = factor(age_group, levels = c("Under 5", "5-19", "20+")))

ggplot(age_long, aes(x = snapshot_date, y = cases, color = age_group)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 1.5) +
  scale_y_continuous(labels = comma) +
  scale_color_manual(values = c("Under 5" = "#e74c3c", "5-19" = "#2980b9", "20+" = "#27ae60")) +
  labs(
    title = "Measles Cases by Age Group",
    subtitle = "Cumulative confirmed cases reported to CDC",
    x = NULL, y = "Cases", color = "Age group"
  ) +
  theme_minimal(base_size = 13) +
  theme(legend.position = "top")

ggsave("plots/cases_by_age.png", width = 9, height = 5, dpi = 200)

# ── 3. Age group proportions over time ───────────────────────────────────────

age_pct <- df |>
  select(snapshot_date, age_under5_pct, age_5_19_pct, age_20plus_pct) |>
  pivot_longer(-snapshot_date, names_to = "age_group", values_to = "pct") |>
  filter(!is.na(pct)) |>
  mutate(age_group = recode(age_group,
    "age_under5_pct" = "Under 5",
    "age_5_19_pct"   = "5-19",
    "age_20plus_pct" = "20+"
  )) |>
  mutate(age_group = factor(age_group, levels = c("Under 5", "5-19", "20+")))

ggplot(age_pct, aes(x = snapshot_date, y = pct, fill = age_group)) +
  geom_area(alpha = 0.8) +
  scale_y_continuous(labels = label_percent(scale = 1)) +
  scale_fill_manual(values = c("Under 5" = "#e74c3c", "5-19" = "#2980b9", "20+" = "#27ae60")) +
  labs(
    title = "Age Distribution of Measles Cases Over Time",
    x = NULL, y = "Percent of cases", fill = "Age group"
  ) +
  theme_minimal(base_size = 13) +
  theme(legend.position = "top")

ggsave("plots/age_distribution.png", width = 9, height = 5, dpi = 200)

# ── 4. Vaccination status over time ─────────────────────────────────────────

vax_long <- df |>
  select(snapshot_date, vax_unvax_or_unknown_pct, vax_one_mmr_pct, vax_two_mmr_pct) |>
  pivot_longer(-snapshot_date, names_to = "vax_status", values_to = "pct") |>
  filter(!is.na(pct)) |>
  mutate(vax_status = recode(vax_status,
    "vax_unvax_or_unknown_pct" = "Unvaccinated / Unknown",
    "vax_one_mmr_pct"          = "One MMR dose",
    "vax_two_mmr_pct"          = "Two MMR doses"
  )) |>
  mutate(vax_status = factor(vax_status,
    levels = c("Two MMR doses", "One MMR dose", "Unvaccinated / Unknown")))

ggplot(vax_long, aes(x = snapshot_date, y = pct, fill = vax_status)) +
  geom_area(alpha = 0.8) +
  scale_y_continuous(labels = label_percent(scale = 1)) +
  scale_fill_manual(values = c(
    "Unvaccinated / Unknown" = "#c0392b",
    "One MMR dose"           = "#f39c12",
    "Two MMR doses"          = "#27ae60"
  )) +
  labs(
    title = "Vaccination Status of Measles Cases Over Time",
    x = NULL, y = "Percent of cases", fill = "Vaccination status"
  ) +
  theme_minimal(base_size = 13) +
  theme(legend.position = "top")

ggsave("plots/vaccination_status.png", width = 9, height = 5, dpi = 200)

# ── 5. Hospitalization rate over time ────────────────────────────────────────

hosp_age <- df |>
  select(snapshot_date, hosp_under5_pct, hosp_5_19_pct, hosp_20plus_pct, hosp_total_pct) |>
  pivot_longer(-snapshot_date, names_to = "group", values_to = "pct") |>
  filter(!is.na(pct)) |>
  mutate(group = recode(group,
    "hosp_total_pct"   = "Overall",
    "hosp_under5_pct"  = "Under 5",
    "hosp_5_19_pct"    = "5-19",
    "hosp_20plus_pct"  = "20+"
  )) |>
  mutate(group = factor(group, levels = c("Under 5", "Overall", "20+", "5-19")))

ggplot(hosp_age, aes(x = snapshot_date, y = pct, color = group)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 1.5) +
  scale_y_continuous(labels = label_percent(scale = 1)) +
  scale_color_manual(values = c(
    "Overall"  = "#1a5276",
    "Under 5"  = "#e74c3c",
    "5-19"     = "#2980b9",
    "20+"      = "#27ae60"
  )) +
  labs(
    title = "Hospitalization Rate by Age Group",
    subtitle = "Percent of cases hospitalized within each age group",
    x = NULL, y = "Hospitalization rate (%)", color = NULL
  ) +
  theme_minimal(base_size = 13) +
  theme(legend.position = "top")

ggsave("plots/hospitalization_rate.png", width = 9, height = 5, dpi = 200)

message("All plots saved to plots/")
