import requests
import json
import datetime
import os

issue_query = """
{
	repository(owner: "HashiCorp", name: "packer") {
		issues(%s){
			edges{
				node{
					createdAt,
					closedAt
				}
				cursor
			}
			pageInfo {
				endCursor
				hasNextPage
			}
		}
  }
}
"""
pull_query = """
{
	repository(owner: "HashiCorp", name: "packer") {
		pullRequests(%s){
			edges{
				node{
					createdAt,
					closedAt
				}
				cursor
			}
			pageInfo {
				endCursor
				hasNextPage
			}
		}
	}
}
"""

def get_open_close_dates(categories):
	def run_query(query):
		headers = {"Authorization": "token %s" % os.getenv("GITHUB_TOKEN")}
		request = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)
		if request.status_code == 200:
			return request.json()
		else:
			raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

	all_issues = []
	for category, query in categories.iteritems():
		result = run_query(query[0] % "first:50")
		print result
		all_issues.extend(result["data"]["repository"][query[1]]["edges"])
		cursor = result["data"]["repository"][query[1]]["pageInfo"]["endCursor"]
		while True:
			if not result["data"]["repository"][query[1]]["pageInfo"]["hasNextPage"]:
				break
			offset_string = "first:50 after:\"%s\"" % cursor
			result = run_query(query[0] % offset_string)
			print result
			if not result["data"]:
				break
			all_issues.extend(result["data"]["repository"][query[1]]["edges"])
			cursor = result["data"]["repository"][query[1]]["pageInfo"]["endCursor"]

		with open("./%s.json" % query[1], "w") as f:
			f.write(json.dumps(all_issues))

def convert_open_close_to_daily_count(categories):
	for category, query in categories.iteritems():
		with open("./%s.json" % query[1], "r") as f:
			datedict = json.loads(f.read())

		# create dictionary where all keys are datetime objects representing each day
		# We will increment the values based on how many issues were open during that
		# time
		day_buckets = {}
		trackday = datetime.datetime.strptime("2013-04-27", "%Y-%m-%d") # first issue
		while trackday <= datetime.datetime.today():
			day_buckets[trackday] = 0
			trackday = trackday + datetime.timedelta(days=1)

		# now loop over issues, incrementing appropriate buckets for each issue
		for n in datedict:
			# example date: "2013-04-27T16:20:21Z"; we don't need the timezone and
			# exact time since we only care about day opened, so strip that part
			# off to ease parsing
			raw_start = n["node"]["createdAt"].split("T")[0]
			start_date = datetime.datetime.strptime(raw_start, "%Y-%m-%d")

			raw_end = n["node"]["closedAt"]
			if raw_end:
				raw_end = raw_end.split("T")[0]
				end_date = datetime.datetime.strptime(raw_end, "%Y-%m-%d")
			else:
				end_date = datetime.datetime.today()

			d = start_date
			while d <= end_date:
				day_buckets[d] += 1
				d = d + datetime.timedelta(days=1)

		with open ("./%s.csv" % query[1], "w") as f:
			for day, count in day_buckets.iteritems():
				f.write(datetime.datetime.strftime(day, "%D") + "," + "%d" %count + "\n")

def main():
	categories = {"issues": [issue_query, "issues"], "pulls": [pull_query, "pullRequests"]}
	get_open_close_dates(categories)
	day_buckets = convert_open_close_to_daily_count(categories)


if __name__ == "__main__":
	main()
