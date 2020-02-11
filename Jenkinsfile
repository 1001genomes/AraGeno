// docs https://confluence.imp.ac.at/display/SD/CICD+for+container+images


buildDockerImage([
    imageName: "arageno",
    pushRegistryNamespace: "nordborglab",
    // enable when there are test cases
    //testCmd: 'py.test -ra -p no:cacheprovider --junitxml ./junit.xml',
    pushBranches: ["master"]
])