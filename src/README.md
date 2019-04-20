# Charm Spark
This charm provides an opinionated yet minimal spark configuration.

### Usage
To deploy this charm:
```bash
juju deploy cs:~omnivector/spark
```
This will configure a single unit to be a master, worker, and history-server.

To add worker nodes to the spark deploy use `juju add-unit`.
```bash
juju add-unit spark -n 3
```

##### License
- GPLv3 (see `LICENSE` file in this directory)

##### Copyright
- Omnivector Solutions &copy; 2018 <admin@omnivector.solutions>
