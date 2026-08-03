namespace TradingViewWebhookDashboard.Models;

public sealed class CorrelationDashboardOptions
{
    public const string SectionName = "CorrelationDashboard";
    public const string DefaultPageTitle = "DOGEUSDT.P 相關係數 (0.7~1.0) 日 K";
    public const string DefaultDisplayTimeZoneId = "Asia/Taipei";

    public string PageTitle { get; set; } = DefaultPageTitle;

    public string BaseSymbol { get; set; } = "DOGEUSDT";

    public string BaseTradingViewSymbol { get; set; } = "DOGEUSDT.P";

    public string ProductType { get; set; } = "usdt-futures";

    public string Granularity { get; set; } = "1D";

    public int CandleLimit { get; set; } = 20;

    public double MinCorrelation { get; set; } = 0.70;

    public double MaxCorrelation { get; set; } = 1.00;

    public int RefreshIntervalMinutes { get; set; } = 15;

    public int MaxParallelRequests { get; set; } = 4;

    public int TopResultCount { get; set; } = 120;

    public string SnapshotPath { get; set; } = "App_Data/correlation-dashboard.json";

    public string DisplayTimeZoneId { get; set; } = DefaultDisplayTimeZoneId;

    public int GetSafeCandleLimit() => Math.Clamp(CandleLimit, 5, 200);

    public TimeSpan GetRefreshInterval() => TimeSpan.FromMinutes(Math.Clamp(RefreshIntervalMinutes, 5, 1440));

    public int GetSafeMaxParallelRequests() => Math.Clamp(MaxParallelRequests, 1, 12);

    public int GetSafeTopResultCount() => Math.Clamp(TopResultCount, 10, 500);

    public TimeZoneInfo GetDisplayTimeZone()
    {
        foreach (var candidate in new[] { DisplayTimeZoneId, DefaultDisplayTimeZoneId, "Taipei Standard Time" })
        {
            if (string.IsNullOrWhiteSpace(candidate))
            {
                continue;
            }

            try
            {
                return TimeZoneInfo.FindSystemTimeZoneById(candidate);
            }
            catch (TimeZoneNotFoundException)
            {
            }
            catch (InvalidTimeZoneException)
            {
            }
        }

        return TimeZoneInfo.CreateCustomTimeZone(
            "UTC+08",
            TimeSpan.FromHours(8),
            "UTC+08",
            "UTC+08");
    }
}
