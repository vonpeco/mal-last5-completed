# Peco MAL analytics pixel (test)

This is a test extension for the existing `peco-mal-updater2` Worker. It keeps the MAL update POST endpoint intact and adds a transparent 1x1 GIF at:

`https://peco-mal-updater2.madcapsoru.workers.dev/pixel.gif`

## What the first test records

If an Analytics Engine binding is configured, each pixel request records:
- Country
- Region/province
- City/locality
- Network/ASN organization reported by Cloudflare
- Referrer hostname, when supplied

It does not store the visitor's raw IP address, full URL, or browser fingerprint.

Location is approximate IP geolocation. Some fields may be blank or inaccurate, especially with VPNs, mobile networks, or intermediary image proxies.

## Configure the Worker

1. Open Cloudflare Dashboard > Workers & Pages > `peco-mal-updater2`.
2. Open Settings > Bindings and add an **Analytics Engine** binding:
   - Variable name: `ANALYTICS`
   - Dataset name: `mal_profile_visits`
3. Open Edit code and replace the Worker code with this file's contents:
   `cloudflare/peco-mal-updater2.js`
4. Deploy the Worker.

Keep the existing `GITHUB_TOKEN` and `UPDATE_SECRET` secrets configured. Do not paste either secret into source code or share them.

## Test

Open this URL in a browser:
`https://peco-mal-updater2.madcapsoru.workers.dev/pixel.gif`

It should display as a blank/transparent 1x1 image. This confirms the endpoint responds, but does not yet prove MAL sends visitor requests directly.

After adding the pixel to the MAL profile and visiting the profile from another browser/network, query the dataset in Cloudflare Analytics Engine. Example SQL for recent requests:

```sql
SELECT
  blob1 AS country,
  blob2 AS region,
  blob3 AS city,
  blob4 AS network,
  blob5 AS referrer,
  SUM(_sample_interval) AS requests
FROM mal_profile_visits
WHERE timestamp > NOW() - INTERVAL '1' DAY
GROUP BY country, region, city, network, referrer
ORDER BY requests DESC
LIMIT 100
```

If the network/location belongs to MAL or another proxy rather than the visitor, stop here: the pixel cannot provide reliable visitor geography through that delivery path.

## Recurrence

Do not enable visitor recurrence counting until the test confirms direct visitor requests. A repeat-visitor metric needs a persistent or pseudonymous identifier; it must be disclosed to profile visitors and should have a limited retention period. The test pixel deliberately does not fingerprint or identify visitors.
