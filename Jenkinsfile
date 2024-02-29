// docs https://confluence.imp.ac.at/display/SD/CICD+for+container+images

def jobsMapping = [
  tags: [jobName:"App AraGeno", jobTags: "reload", extraVars: "app_generic_image_tag: latest"],
  master: [jobName:"App AraGeno", jobTags: "reload", extraVars: "app_generic_image_tag: master"]
]

buildDockerImage([
    imageName: "arageno",
    pushRegistryNamespace: "the1001genomes",
    // enable when there are test cases
    //testCmd: 'py.test -ra -p no:cacheprovider --junitxml ./junit.xml',
    pushBranches: ["master"],
    tower: jobsMapping
])
