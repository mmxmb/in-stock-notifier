THIS_FILE := $(lastword $(MAKEFILE_LIST))

.PHONY: build invoke-prod invoke-dev deploy test update cleanup

build:
	pipenv lock -r > requirements.txt 
	sam build --manifest requirements.txt
	rm requirements.txt

invoke-prod:
	@$(MAKE) -f $(THIS_FILE) check-env
	@$(MAKE) -f $(THIS_FILE) build
	sam local invoke --parameter-overrides \
	Dev=false \
 	EmailFrom=${EMAIL_FROM} \
	EmailTo=${EMAIL_TO}

invoke-dev:
	@$(MAKE) -f $(THIS_FILE) check-env
	@$(MAKE) -f $(THIS_FILE) build
	sam local invoke --parameter-overrides \
	Dev=true \
 	EmailFrom=${EMAIL_FROM} \
	EmailTo=${EMAIL_TO}

deploy:
	@$(MAKE) -f $(THIS_FILE) check-env
	@$(MAKE) -f $(THIS_FILE) build
	sam deploy	--stack-name in-stock-notifier \
	--guided \
	--parameter-overrides \
	Dev=false \
 	EmailFrom=${EMAIL_FROM} \
	EmailTo=${EMAIL_TO}

test:
	pytest in_stock_notifier

cleanup:
	aws cloudformation delete-stack --stack-name in-stock-notifier
	aws dynamodb delete-table --table-name in-stock-notifications

check-env:
ifndef EMAIL_FROM
	$(error EMAIL_FROM envvar is undefined)
endif
ifndef EMAIL_TO
	$(error EMAIL_TO envvar is undefined)
endif
