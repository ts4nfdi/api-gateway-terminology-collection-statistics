# Collection Statistics Service

The Collection Statistics Service calculates statistics for terminology collections provided by the Base4NFDI Terminology Service.

For each collection, the service retrieves statistics from the corresponding terminology providers and counts:

- RDF Properties
- OWL Classes
- OWL Named Individuals
- SKOS Concepts

The calculated statistics are stored in a PostgreSQL database.

## Database Setup

The service stores the calculated statistics in a PostgreSQL table named `collection_statistics`.

Before deploying the service, create the following table in the target database:

```sql
CREATE TABLE IF NOT EXISTS collection_statistics (
    collection_id UUID NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    terminology_count BIGINT NOT NULL,
    property_count BIGINT NOT NULL,
    class_count BIGINT NOT NULL,
    named_individual_count BIGINT NOT NULL,
    concept_count BIGINT NOT NULL,
    PRIMARY KEY (collection_id, "timestamp")
);
```
Important: The table and column names must match those expected by the service exactly; otherwise, database operations will fail.

## API

The service runs on port `8000` and provides two endpoints.

- ### Calculate statistics for selected collections

`POST /stats?collection=<collection-id>`

Multiple collections can be specified:

`POST /stats?collection=<collection-id-1>&collection=<collection-id-2>`

- ### Calculate statistics for all collections

`POST /stats/all`

## Docker

The Docker image is built automatically by the GitHub Actions workflow in `.github/workflows/publish-docker.yml` on every push to `main`. The workflow can also be triggered manually via GitHub Actions.

The image is published to the GitHub Container Registry (GHCR) at:

```text
ghcr.io/ts4nfdi/api-gateway-terminology-collection-statistics:latest
ghcr.io/ts4nfdi/api-gateway-terminology-collection-statistics:<commit-sha>
```
## Kubernetes Deployment

The Kubernetes configuration is located in the `k8s/` directory.

It contains:

- `deployment.yaml` – deploys the Collection Statistics container and references the existing database and API-key Secrets in the target cluster
- `service.yaml` – exposes the deployed pods through a Kubernetes Service

The deployment is intended for the target Kubernetes cluster, where the required Secrets and PostgreSQL service already exist.

Select the target cluster context and deploy the Kubernetes resources to the appropriate namespace:

```bash
kubectl apply -n <namespace> -f k8s/
```

Check the deployment:

```bash
kubectl get pods -n <namespace>
```

```bash
kubectl get services -n <namespace>
```

## Accessing the Service

Inside the Kubernetes cluster, the service is reachable at:

`http://ts4nfdi-api-gateway-collection-statistics:8000`

The service currently uses the Kubernetes `ClusterIP` type and is therefore only directly reachable from inside the cluster.

## Testing in Kubernetes

For testing you can create a test client:

```bash
kubectl run test-client -n <namespace> --restart=Never --image=curlimages/curl -- curl -X POST http://ts4nfdi-api-gateway-collection-statistics:8000/stats/all
```

Check the output of the test client and service:

```bash
kubectl logs -n <namespace> test-client
```

```bash
kubectl logs -n <namespace> ts4nfdi-api-gateway-collection-statistics-<podnumber>
```

Delete the test-client:
```bash
kubectl delete pod test-client -n <namespace>
```
## Running the script locally

You can run `collectionStats.py` directly to test the statistics calculation without starting the HTTP service:

```bash
python src/collectionStats.py
```

By default, the script processes all collections and attempts to write the calculated statistics to PostgreSQL. To enable database writes when running locally, you must configure the required database environment variables yourself (`DB_URL`, `DB_USERNAME`, and `DB_PASSWORD`). Provider API keys must also be set if the selected collections require them.

To calculate statistics without writing to the database, use `--no-db`:

```bash
python src/collectionStats.py --no-db
```

You can optionally pass one or more collection IDs to process only those collections:

```bash
python src/collectionStats.py --no-db <collection-id-1> <collection-id-2>
```

The results and any processing errors are printed to the terminal. The `--no-db` option skips the database write but does not bypass provider API-key requirements.

## Project Structure

`server.py` provides the HTTP interface.

`collectionStats.py` retrieves the terminology statistics and stores the calculated collection statistics in PostgreSQL.
